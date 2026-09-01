"""Deterministic comparison reports and single-input failure bundles."""

from __future__ import annotations

import copy
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import tempfile
from typing import Iterable, Protocol
import xml.etree.ElementTree as ET

from .canonical import JSONValue, atomic_write, dump_bytes, dumps, sha256_bytes, write_jsonl
from .cases import CaseRegistry, load_case_definitions
from .errors import ValidationError
from .isa import ISARegistry, project_used_isa
from .records import derive_input_id


class InputArtifactLike(Protocol):
    manifest: dict[str, JSONValue]
    manifest_path: Path
    records: tuple[dict[str, JSONValue], ...]


class ResultArtifactLike(Protocol):
    manifest: dict[str, JSONValue]
    manifest_path: Path
    records: dict[str, dict[str, JSONValue]]


class ComparisonLike(Protocol):
    outcome: str
    mismatch_count: int
    first_difference: dict[str, JSONValue] | None
    reason: str | None


@dataclass(frozen=True)
class RecordReport:
    case_id: str
    input_id: str
    comparison: ComparisonLike
    failure_path: str | None = None


@dataclass(frozen=True)
class ReportFiles:
    summary_path: Path
    junit_path: Path


def write_reports(output: str | Path, reports: Iterable[RecordReport]) -> ReportFiles:
    """Write a small non-normative summary and deterministic JUnit XML."""

    destination = Path(output)
    destination.mkdir(parents=True, exist_ok=True)
    ordered = sorted(reports, key=lambda item: (item.case_id, item.input_id))
    matched = sum(item.comparison.outcome == "match" for item in ordered)
    mismatched = sum(item.comparison.outcome == "mismatch" for item in ordered)
    not_comparable = sum(item.comparison.outcome == "not_comparable" for item in ordered)
    mismatch_atoms = sum(
        item.comparison.mismatch_count
        for item in ordered
        if item.comparison.outcome == "mismatch"
    )
    outcome = "pass"
    if not_comparable:
        outcome = "not_comparable"
    elif mismatched:
        outcome = "mismatch"
    failures = [item.failure_path for item in ordered if item.failure_path is not None]
    summary: dict[str, JSONValue] = {
        "artifact_type": "ioitf.comparison-summary",
        "failure_bundles": failures,
        "matched_inputs": matched,
        "mismatch_atoms": mismatch_atoms,
        "mismatched_inputs": mismatched,
        "not_comparable_inputs": not_comparable,
        "outcome": outcome,
        "record_count": len(ordered),
        "schema_version": 1,
    }
    suite = ET.Element(
        "testsuite",
        {
            "name": "intrinsics-equivalence",
            "tests": str(len(ordered)),
            "failures": str(mismatched),
            "errors": str(not_comparable),
        },
    )
    for item in ordered:
        test = ET.SubElement(
            suite,
            "testcase",
            {"classname": item.case_id, "name": item.input_id},
        )
        comparison = item.comparison
        if comparison.outcome == "mismatch":
            node = ET.SubElement(test, "failure", {"message": "intrinsic result mismatch"})
            node.text = dumps(comparison.first_difference or {})
        elif comparison.outcome == "not_comparable":
            node = ET.SubElement(test, "error", {"message": "results are not comparable"})
            node.text = comparison.reason or "both runners returned a non-ok result"
    ET.indent(suite, space="  ")
    xml = ET.tostring(suite, encoding="utf-8", xml_declaration=True) + b"\n"
    junit_path = destination / "junit.xml"
    atomic_write(junit_path, xml)
    # summary.json is the comparison-level completion marker and is last.
    summary_path = destination / "summary.json"
    atomic_write(summary_path, dump_bytes(summary, newline=True))
    return ReportFiles(summary_path, junit_path)


def _single_result_manifest(
    source: dict[str, JSONValue],
    *,
    case_id: str,
    rounding: str,
    input_sha: str,
    case_sha: str,
    used_sha: str,
    file_name: str,
    byte_length: int,
    result_sha: str,
) -> dict[str, JSONValue]:
    manifest = copy.deepcopy(source)
    manifest["case_definitions_sha256"] = case_sha
    manifest["input_sha256"] = input_sha
    manifest["used_isa_contract_sha256"] = used_sha
    environment = manifest["environment"]
    assert isinstance(environment, dict)
    environment["fp_rounding_modes"] = [rounding]
    case_build_units = environment["case_build_units"]
    if not isinstance(case_build_units, dict) or case_id not in case_build_units:
        raise ValidationError(f"result manifest has no build-unit mapping for {case_id!r}")
    environment["case_build_units"] = {case_id: case_build_units[case_id]}
    manifest["results"] = {
        "byte_length": byte_length,
        "file": file_name,
        "record_count": 1,
        "sha256": result_sha,
    }
    return manifest


def write_failure_bundle(
    *,
    output: str | Path,
    input_artifact: InputArtifactLike,
    intel_artifact: ResultArtifactLike,
    openpower_artifact: ResultArtifactLike,
    cases: CaseRegistry,
    isa_registry: ISARegistry,
    input_record: dict[str, JSONValue],
    comparison: ComparisonLike,
) -> Path:
    """Publish one fully projected failure bundle, with ``failure.json`` last."""

    if comparison.outcome != "mismatch" or comparison.first_difference is None:
        raise ValidationError("failure bundles require an ordinary mismatch")
    input_id = str(input_record["input_id"])
    case_id = str(input_record["case_id"])
    if input_id not in intel_artifact.records or input_id not in openpower_artifact.records:
        raise ValidationError("cannot bundle a result missing from either role")
    case = cases.get(case_id)
    failures = Path(output) / "failures"
    failures.mkdir(parents=True, exist_ok=True)
    final_directory = failures / input_id
    if final_directory.exists():
        raise ValidationError(f"refusing to replace an existing failure bundle: {final_directory}")
    temporary = Path(tempfile.mkdtemp(prefix=f".{input_id}.", dir=failures))
    try:
        contracts = temporary / "contracts"
        baseline_intel = temporary / "baseline" / "intel"
        baseline_power = temporary / "baseline" / "openpower"
        contracts.mkdir(parents=True)
        baseline_intel.mkdir(parents=True)
        baseline_power.mkdir(parents=True)

        single_input = copy.deepcopy(input_record)
        single_input["sequence"] = 1
        if derive_input_id(single_input) != input_id:
            raise ValidationError("sequence projection unexpectedly changed input_id")
        _, input_length, input_sha = write_jsonl(
            temporary / "test-vectors.jsonl", [single_input]
        )
        case_data: list[JSONValue] = [case.data]
        case_bytes = dump_bytes(case_data, newline=True)
        case_sha = sha256_bytes(case_bytes)
        atomic_write(contracts / "case-definitions.json", case_bytes)
        used = project_used_isa(isa_registry, [case])
        atomic_write(contracts / "isa-used.json", dump_bytes(used.data, newline=True))

        source_input = input_artifact.manifest
        input_manifest: dict[str, JSONValue] = {
            "artifact_type": "ioitf.test-vectors",
            "case_definitions_sha256": case_sha,
            "complete": True,
            "isa_registry_sha256": source_input["isa_registry_sha256"],
            "profile": source_input["profile"],
            "schema_version": 1,
            "test_vectors": {
                "byte_length": input_length,
                "file": "test-vectors.jsonl",
                "record_count": 1,
                "sha256": input_sha,
            },
            "used_isa_contract_sha256": used.sha256,
        }
        atomic_write(
            temporary / "test-vectors.manifest.json",
            dump_bytes(input_manifest, newline=True),
        )

        intel_record = intel_artifact.records[input_id]
        power_record = openpower_artifact.records[input_id]
        _, intel_length, intel_sha = write_jsonl(
            baseline_intel / "intel-results.jsonl", [intel_record]
        )
        _, power_length, power_sha = write_jsonl(
            baseline_power / "power-results.jsonl", [power_record]
        )
        environment = input_record["environment"]
        assert isinstance(environment, dict)
        rounding = str(environment["rounding"])
        intel_manifest = _single_result_manifest(
            intel_artifact.manifest,
            case_id=case_id,
            rounding=rounding,
            input_sha=input_sha,
            case_sha=case_sha,
            used_sha=used.sha256,
            file_name="intel-results.jsonl",
            byte_length=intel_length,
            result_sha=intel_sha,
        )
        power_manifest = _single_result_manifest(
            openpower_artifact.manifest,
            case_id=case_id,
            rounding=rounding,
            input_sha=input_sha,
            case_sha=case_sha,
            used_sha=used.sha256,
            file_name="power-results.jsonl",
            byte_length=power_length,
            result_sha=power_sha,
        )
        atomic_write(
            baseline_intel / "intel-results.manifest.json",
            dump_bytes(intel_manifest, newline=True),
        )
        atomic_write(
            baseline_power / "power-results.manifest.json",
            dump_bytes(power_manifest, newline=True),
        )

        source_vectors = source_input["test_vectors"]
        source_intel_results = intel_artifact.manifest["results"]
        source_power_results = openpower_artifact.manifest["results"]
        assert isinstance(source_vectors, dict)
        assert isinstance(source_intel_results, dict)
        assert isinstance(source_power_results, dict)
        failure: dict[str, JSONValue] = {
            "abi_version": 1,
            "artifact_type": "ioitf.failure",
            "baseline": {
                "intel_manifest": "baseline/intel/intel-results.manifest.json",
                "openpower_manifest": "baseline/openpower/power-results.manifest.json",
            },
            "case_definitions_sha256": case_sha,
            "case_id": case_id,
            "comparison": case.comparison,
            "contracts": {
                "case_definitions": {
                    "file": "contracts/case-definitions.json",
                    "sha256": case_sha,
                },
                "used_isa": {"file": "contracts/isa-used.json", "sha256": used.sha256},
            },
            "first_difference": comparison.first_difference,
            "input_id": input_id,
            "mismatch_count": comparison.mismatch_count,
            "reproduce": {
                "intel": [
                    "ioitf", "replay", "--failure", "failure.json", "--role", "intel",
                    "--output", "replay/intel",
                ],
                "openpower": [
                    "ioitf", "replay", "--failure", "failure.json", "--role", "openpower",
                    "--output", "replay/openpower",
                ],
                "verify": [
                    "ioitf", "verify-replay", "--failure", "failure.json", "--intel",
                    "replay/intel/intel-results.manifest.json", "--openpower",
                    "replay/openpower/power-results.manifest.json",
                ],
            },
            "schema_version": 1,
            "source_artifacts": {
                "case_definitions_sha256": source_input["case_definitions_sha256"],
                "input_isa_registry_sha256": source_input["isa_registry_sha256"],
                "input_sha256": source_vectors["sha256"],
                "intel_isa_registry_sha256": intel_artifact.manifest["isa_registry_sha256"],
                "intel_results_sha256": source_intel_results["sha256"],
                "openpower_isa_registry_sha256": openpower_artifact.manifest["isa_registry_sha256"],
                "openpower_results_sha256": source_power_results["sha256"],
                "used_isa_contract_sha256": source_input["used_isa_contract_sha256"],
            },
            "test_vectors_manifest": "test-vectors.manifest.json",
            "used_isa_contract_sha256": used.sha256,
        }

        # Validate the three projected artifacts before publishing failure.json.
        from .artifacts import validate_input_artifact, validate_result_artifact

        bundle_cases = load_case_definitions(
            contracts / "case-definitions.json", isa_registry=isa_registry
        )
        bundle_input = validate_input_artifact(
            temporary / "test-vectors.manifest.json", bundle_cases, isa_registry
        )
        validate_result_artifact(
            baseline_intel / "intel-results.manifest.json",
            bundle_cases,
            isa_registry,
            input_artifact=bundle_input,
        )
        validate_result_artifact(
            baseline_power / "power-results.manifest.json",
            bundle_cases,
            isa_registry,
            input_artifact=bundle_input,
        )
        atomic_write(temporary / "failure.json", dump_bytes(failure, newline=True))
        os.replace(temporary, final_directory)
        return final_directory
    except BaseException:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
