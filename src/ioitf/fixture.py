"""Explicitly non-conformant development runner used to test the coordinator.

The fixture writes schema-shaped artifacts, but its build ID is permanently
prefixed with ``development-fixture:``.  Comparison rejects those artifacts
unless the caller explicitly opts in.  It must never be presented as native
x86_64 or ppc64le execution evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import struct
from typing import Protocol

from .canonical import (
    JSONValue,
    atomic_write,
    dump_bytes,
    remove_completion_marker,
    sha256_bytes,
    utf16_sort_key,
    write_jsonl,
)
from .cases import CaseRegistry
from .errors import UnsupportedError, ValidationError
from .isa import ISARegistry, project_used_isa
from .records import validate_result_record


class InputArtifactLike(Protocol):
    manifest: dict[str, JSONValue]
    records: tuple[dict[str, JSONValue], ...]


@dataclass(frozen=True)
class FixtureRunResult:
    output_directory: Path
    manifest_path: Path
    results_path: Path
    record_count: int
    sha256: str


def _f64_from_bits(bits: str) -> float:
    return struct.unpack(">d", int(bits, 16).to_bytes(8, "big"))[0]


def _f64_bits(value: float) -> str:
    integer = int.from_bytes(struct.pack(">d", value), "big")
    return f"0x{integer:016x}"


def _execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    case_id = str(record["case_id"])
    operands = record["operands"]
    assert isinstance(operands, dict)

    if case_id == "sse2.add.f64x2.default":
        left = operands["a"]
        right = operands["b"]
        assert isinstance(left, dict) and isinstance(right, dict)
        left_lanes = left["lanes"]
        right_lanes = right["lanes"]
        assert isinstance(left_lanes, list) and isinstance(right_lanes, list)
        lanes = [
            _f64_bits(_f64_from_bits(str(a)) + _f64_from_bits(str(b)))
            for a, b in zip(left_lanes, right_lanes, strict=True)
        ]
        return {"return": {"element": "f64", "lanes": lanes}}

    if case_id == "sse2.set1.f64x2.default":
        value = operands["value"]
        assert isinstance(value, dict)
        bits = str(value["bits"])
        return {"return": {"element": "f64", "lanes": [bits, bits]}}

    if case_id == "sse2.shuffle.i32x4.imm8":
        source = operands["a"]
        immediates = record["immediates"]
        assert isinstance(source, dict) and isinstance(immediates, dict)
        source_lanes = source["lanes"]
        assert isinstance(source_lanes, list)
        control = int(immediates["imm8"])
        lanes = [str(source_lanes[(control >> (2 * lane)) & 3]) for lane in range(4)]
        return {"return": {"element": "i32", "lanes": lanes}}

    raise UnsupportedError(f"development fixture has no implementation for {case_id!r}")


def _result_records(
    input_artifact: InputArtifactLike,
    *,
    cases: CaseRegistry,
    role: str,
) -> list[dict[str, JSONValue]]:
    results: list[dict[str, JSONValue]] = []
    for input_record in input_artifact.records:
        case = cases.get(str(input_record["case_id"]))
        result: dict[str, JSONValue] = {
            "case_id": case.id,
            "duration_ns": 0,
            "input_id": input_record["input_id"],
            "observed": _execute(input_record),
            "runner": role,
            "schema_version": 1,
            "status": "ok",
        }
        validate_result_record(result, case, role=role, input_record=input_record)
        results.append(result)
    return results


def _probe(architecture: str, roundings: list[str]) -> dict[str, JSONValue]:
    controls: dict[str, JSONValue]
    if architecture == "x86_64":
        controls = {
            "exception_traps_enabled": False,
            "mxcsr_daz": False,
            "mxcsr_ftz": False,
        }
    else:
        controls = {
            "exception_traps_enabled": False,
            "fpscr_ni": False,
            "vscr_nj": False,
        }
    suite: list[JSONValue] = [
        {
            "architecture": architecture,
            "expected": {
                "boolean_controls": controls,
                "fp_exception_flags": [],
                "rounding_modes": roundings,
            },
            "id": "fixture-controls.v1",
            "implementation_id": "development.fixture.v1",
            "version": 1,
        }
    ]
    return {
        "probe_suite": suite,
        "probe_suite_sha256": sha256_bytes(dump_bytes(suite, newline=True)),
        "probes": [{"id": "fixture-controls.v1", "status": "passed"}],
        "status": "passed",
    }


def _environment(
    *,
    role: str,
    cases: CaseRegistry,
    isa_registry: ISARegistry,
    records: tuple[dict[str, JSONValue], ...],
) -> dict[str, JSONValue]:
    architecture = "x86_64" if role == "intel" else "ppc64le"
    required: set[str] = set()
    case_ids = {str(record["case_id"]) for record in records}
    for case_id in case_ids:
        case = cases.get(case_id)
        required.update(isa_registry.closure(case.required_isa(role), architecture=architecture))
    available = sorted(required, key=utf16_sort_key)
    roundings = sorted(
        {
            str(record["environment"]["rounding"])
            for record in records
            if isinstance(record["environment"], dict)
        },
        key=utf16_sort_key,
    )
    source_path = Path(__file__)
    source_digest = sha256_bytes(source_path.read_bytes())
    compiler: dict[str, JSONValue] = {
        "name": "cpython",
        "target_triple": "non-native-development-fixture",
        "version": platform.python_version(),
    }
    unit: dict[str, JSONValue] = {
        "assertions_enabled": False,
        "compile_options": [],
        "compiler": compiler,
        "feature_macros": {},
        "id": "development.fixture",
        "kind": "support",
        "object_sha256": source_digest,
        "source_blob_sha256": source_digest,
    }
    controls: dict[str, JSONValue]
    if role == "intel":
        controls = {
            "exception_traps_enabled": False,
            "mxcsr_daz": False,
            "mxcsr_ftz": False,
        }
    else:
        controls = {
            "exception_traps_enabled": False,
            "fpscr_ni": False,
            "vscr_nj": False,
        }
    environment: dict[str, JSONValue] = {
        "architecture": architecture,
        "assertions_enabled": False,
        "available_isa": available,
        "build_units": [unit],
        "case_build_units": {
            case_id: ["development.fixture"]
            for case_id in sorted(case_ids, key=utf16_sort_key)
        },
        "cpu_model": "non-native-development-fixture",
        "endianness": "little",
        "fp_controls": controls,
        "fp_rounding_modes": roundings,
        "git_commit": "0" * 40,
        "kernel": "non-native-development-fixture",
        "link": {
            "binary_sha256": source_digest,
            "link_options": [],
            "loaded_libraries": [],
        },
        "os": "linux",
    }
    if role == "openpower":
        environment["vector_semantics"] = {
            "altivec_src_compat": "unknown",
            "element_reg_order": "unknown",
        }
    return environment


def run_fixture(
    *,
    input_artifact: InputArtifactLike,
    cases: CaseRegistry,
    isa_registry: ISARegistry,
    role: str,
    output: str | Path,
) -> FixtureRunResult:
    """Execute the portable fixture and publish a complete result artifact."""

    if role not in {"intel", "openpower"}:
        raise ValidationError("fixture role must be intel or openpower")
    if not input_artifact.records:
        raise ValidationError("fixture input artifact is empty")
    output_directory = Path(output)
    output_directory.mkdir(parents=True, exist_ok=True)
    stem = "intel" if role == "intel" else "power"
    results_path = output_directory / f"{stem}-results.jsonl"
    manifest_path = output_directory / f"{stem}-results.manifest.json"
    remove_completion_marker(manifest_path)

    results = _result_records(input_artifact, cases=cases, role=role)
    count, byte_length, results_sha = write_jsonl(results_path, results)
    if count != len(input_artifact.records):
        raise ValidationError("fixture result count differs from input record count")
    case_ids = {str(record["case_id"]) for record in input_artifact.records}
    selected = [cases.get(case_id) for case_id in sorted(case_ids, key=utf16_sort_key)]
    used = project_used_isa(isa_registry, selected)
    input_manifest = input_artifact.manifest
    input_vectors = input_manifest["test_vectors"]
    assert isinstance(input_vectors, dict)
    architecture = "x86_64" if role == "intel" else "ppc64le"
    roundings = sorted(
        {
            str(record["environment"]["rounding"])
            for record in input_artifact.records
            if isinstance(record["environment"], dict)
        },
        key=utf16_sort_key,
    )
    manifest: dict[str, JSONValue] = {
        "artifact_type": "ioitf.runner-results",
        "case_definitions_sha256": cases.projected_sha256(case_ids),
        "complete": True,
        "environment": _environment(
            role=role,
            cases=cases,
            isa_registry=isa_registry,
            records=input_artifact.records,
        ),
        "input_sha256": input_vectors["sha256"],
        "isa_registry_sha256": isa_registry.sha256,
        "preflight": _probe(architecture, roundings),
        "results": {
            "byte_length": byte_length,
            "file": results_path.name,
            "record_count": count,
            "sha256": results_sha,
        },
        "runner": {
            "abi_version": 1,
            "build_id": f"development-fixture:{role}:python-v1",
            "role": role,
        },
        "schema_version": 1,
        "used_isa_contract_sha256": used.sha256,
    }
    atomic_write(manifest_path, dump_bytes(manifest, newline=True))
    return FixtureRunResult(output_directory, manifest_path, results_path, count, results_sha)
