"""Command-line coordinator for IOITF artifacts."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys
from typing import Sequence

from .canonical import JSONValue, atomic_write, dump_bytes, dumps
from .cases import CaseRegistry, load_case_definitions
from .errors import (
    EXIT_MATCH,
    EXIT_MISMATCH,
    EXIT_RUNNER,
    EXIT_SPECIFICATION,
    EXIT_UNSUPPORTED,
    IOITFError,
    ReferenceOracleError,
    RunnerError,
    UnsupportedError,
    ValidationError,
)
from .generator import DEFAULT_SEED, generate_artifact
from .isa import ISARegistry, load_isa_registry
from .records import derive_input_id


def _contracts(args: argparse.Namespace) -> tuple[CaseRegistry, ISARegistry]:
    isa = load_isa_registry(args.isa_registry)
    cases = load_case_definitions(args.cases, isa_registry=isa)
    return cases, isa


def _print(value: JSONValue) -> None:
    print(dumps(value))


def _validate_cases(args: argparse.Namespace) -> int:
    cases, isa = _contracts(args)
    _print(
        {
            "case_count": len(cases),
            "case_definitions_sha256": cases.sha256,
            "case_ids": list(cases.ids),
            "isa_registry_sha256": isa.sha256,
            "status": "valid",
        }
    )
    return EXIT_MATCH


def _generate_vectors(args: argparse.Namespace) -> int:
    cases, isa = _contracts(args)
    result = generate_artifact(
        cases=cases,
        isa_registry=isa,
        output=args.output,
        profile=args.profile,
        count_per_case=args.count_per_case,
        seed=args.seed,
    )
    _print(
        {
            "case_definitions_sha256": result.case_definitions_sha256,
            "manifest": str(result.manifest_path),
            "record_count": result.record_count,
            "sha256": result.sha256,
            "status": "generated",
            "used_isa_contract_sha256": result.used_isa_contract.sha256,
        }
    )
    return EXIT_MATCH


def _validate_artifact(args: argparse.Namespace) -> int:
    from .artifacts import validate_input_artifact, validate_result_artifact

    cases, isa = _contracts(args)
    if args.kind == "input":
        artifact = validate_input_artifact(args.manifest, cases, isa)
        _print(
            {
                "kind": "input",
                "manifest": str(artifact.manifest_path),
                "record_count": len(artifact.records),
                "status": "valid",
            }
        )
        return EXIT_MATCH
    if args.input is None:
        raise ValidationError("--input is required when validating a result artifact")
    input_artifact = validate_input_artifact(args.input, cases, isa)
    try:
        artifact = validate_result_artifact(
            args.manifest, cases, isa, input_artifact=input_artifact
        )
    except ValidationError as exc:
        raise RunnerError(f"invalid runner result artifact: {exc}") from exc
    _print(
        {
            "development_fixture": artifact.development_fixture,
            "kind": "result",
            "manifest": str(artifact.manifest_path),
            "record_count": len(artifact.records),
            "role": artifact.role,
            "status": "valid",
        }
    )
    return EXIT_MATCH


def _fixture_run(args: argparse.Namespace) -> int:
    from .artifacts import validate_input_artifact, validate_result_artifact
    from .fixture import run_fixture

    if not args.i_understand_this_is_not_native_evidence:
        raise UnsupportedError(
            "fixture-run requires --i-understand-this-is-not-native-evidence"
        )
    cases, isa = _contracts(args)
    input_artifact = validate_input_artifact(args.input, cases, isa)
    result = run_fixture(
        input_artifact=input_artifact,
        cases=cases,
        isa_registry=isa,
        role=args.role,
        output=args.output,
    )
    try:
        validated = validate_result_artifact(
            result.manifest_path,
            cases,
            isa,
            input_artifact=input_artifact,
        )
    except ValidationError as exc:
        raise RunnerError(f"fixture produced an invalid result artifact: {exc}") from exc
    if not validated.development_fixture:
        raise ValidationError("fixture output did not retain its development marker")
    _print(
        {
            "manifest": str(result.manifest_path),
            "native_evidence": False,
            "record_count": result.record_count,
            "role": args.role,
            "sha256": result.sha256,
            "status": "fixture_complete",
        }
    )
    return EXIT_MATCH


def _reference_oracle_check(
    *,
    output: Path,
    input_artifact: object,
    intel_artifact: object,
    cases: CaseRegistry,
) -> None:
    input_records = getattr(input_artifact, "records")
    intel_records = getattr(intel_artifact, "records")
    input_manifest = getattr(input_artifact, "manifest")
    intel_manifest = getattr(intel_artifact, "manifest")
    inputs_by_id = {str(record["input_id"]): record for record in input_records}

    def fail(input_record: dict[str, JSONValue], regression_id: str, reason: str) -> None:
        vectors = input_manifest["test_vectors"]
        results = intel_manifest["results"]
        assert isinstance(vectors, dict) and isinstance(results, dict)
        reference_error: dict[str, JSONValue] = {
            "artifact_type": "ioitf.reference-error",
            "case_definitions_sha256": input_manifest["case_definitions_sha256"],
            "input_id": input_record["input_id"],
            "input_sha256": vectors["sha256"],
            "intel_results_sha256": results["sha256"],
            "regression_id": regression_id,
            "schema_version": 1,
        }
        output.mkdir(parents=True, exist_ok=True)
        atomic_write(output / "reference-error.json", dump_bytes(reference_error, newline=True))
        raise ReferenceOracleError(reason)

    for input_record in input_records:
        generation = input_record["generation"]
        assert isinstance(generation, dict)
        if generation["class"] != "regression":
            continue
        regression_id = str(generation["regression_id"])
        case = cases.get(str(input_record["case_id"]))
        regressions = case.data["regressions"]
        assert isinstance(regressions, dict)
        regression = regressions[regression_id]
        assert isinstance(regression, dict)
        expected = regression["expected_intel"]
        actual_record = intel_records[str(input_record["input_id"])]
        actual: dict[str, JSONValue] = {"status": actual_record["status"]}
        if actual_record["status"] == "ok":
            actual["observed"] = actual_record["observed"]
        if actual == expected:
            environment = input_record["environment"]
            assert isinstance(environment, dict)
            if environment["rounding"] == "nearest_even":
                continue

            nearest_record = copy.deepcopy(input_record)
            nearest_environment = nearest_record["environment"]
            assert isinstance(nearest_environment, dict)
            nearest_environment["rounding"] = "nearest_even"
            nearest_id = derive_input_id(nearest_record)
            nearest_input = inputs_by_id.get(nearest_id)
            if nearest_input is None:
                fail(
                    input_record,
                    regression_id,
                    f"rounding witness {input_record['input_id']} has no nearest-even pair",
                )
            nearest_result = intel_records[nearest_id]
            if nearest_result["status"] != "ok":
                fail(
                    input_record,
                    regression_id,
                    f"nearest-even baseline {nearest_id} did not produce an Intel value",
                )
            expected_observed = expected["observed"]
            nearest_observed = nearest_result["observed"]
            assert isinstance(expected_observed, dict) and isinstance(nearest_observed, dict)
            expected_value = {
                key: expected_observed[key]
                for key in ("buffers", "return")
                if key in expected_observed
            }
            nearest_value = {
                key: nearest_observed[key]
                for key in ("buffers", "return")
                if key in nearest_observed
            }
            if expected_value == nearest_value:
                fail(
                    input_record,
                    regression_id,
                    f"rounding witness {input_record['input_id']} does not differ "
                    "from its nearest-even Intel baseline",
                )
            continue
        fail(
            input_record,
            regression_id,
            f"Intel regression oracle failed for {input_record['input_id']}",
        )


def _compare_results(args: argparse.Namespace) -> int:
    from .artifacts import validate_input_artifact, validate_result_artifact
    from .compare import compare_result_records
    from .report import RecordReport, write_failure_bundle, write_reports

    cases, isa = _contracts(args)
    input_artifact = validate_input_artifact(args.input, cases, isa)
    try:
        intel_artifact = validate_result_artifact(
            args.intel, cases, isa, input_artifact=input_artifact
        )
    except ValidationError as exc:
        raise RunnerError(f"invalid Intel result artifact: {exc}") from exc
    try:
        power_artifact = validate_result_artifact(
            args.openpower, cases, isa, input_artifact=input_artifact
        )
    except ValidationError as exc:
        raise RunnerError(f"invalid OpenPOWER result artifact: {exc}") from exc
    if intel_artifact.role != "intel" or power_artifact.role != "openpower":
        raise ValidationError("result artifact roles do not match their command arguments")
    if (
        intel_artifact.development_fixture or power_artifact.development_fixture
    ) and not args.allow_development_fixtures:
        raise UnsupportedError(
            "development fixture artifacts require --allow-development-fixtures"
        )

    output = Path(args.output)
    for completion_marker in ("reference-error.json", "summary.json"):
        if (output / completion_marker).exists():
            raise ValidationError(
                f"comparison output already contains {completion_marker}; use a fresh directory"
            )
    _reference_oracle_check(
        output=output,
        input_artifact=input_artifact,
        intel_artifact=intel_artifact,
        cases=cases,
    )
    reports: list[RecordReport] = []
    saw_unsupported = False
    for input_record in input_artifact.records:
        input_id = str(input_record["input_id"])
        intel_record = intel_artifact.records[input_id]
        power_record = power_artifact.records[input_id]
        saw_unsupported = saw_unsupported or (
            intel_record["status"] == "unsupported"
            or power_record["status"] == "unsupported"
        )
        case = cases.get(str(input_record["case_id"]))
        comparison = compare_result_records(
            case,
            input_record,
            intel_record,
            power_record,
            validate=False,
        )
        failure_path: str | None = None
        if comparison.outcome == "mismatch":
            bundle = write_failure_bundle(
                output=output,
                input_artifact=input_artifact,
                intel_artifact=intel_artifact,
                openpower_artifact=power_artifact,
                cases=cases,
                isa_registry=isa,
                input_record=input_record,
                comparison=comparison,
            )
            failure_path = str(bundle.relative_to(output) / "failure.json")
        reports.append(RecordReport(case.id, input_id, comparison, failure_path))

    files = write_reports(output, reports)
    mismatch_count = sum(item.comparison.outcome == "mismatch" for item in reports)
    not_comparable = sum(
        item.comparison.outcome == "not_comparable" for item in reports
    )
    _print(
        {
            "junit": str(files.junit_path),
            "mismatched_inputs": mismatch_count,
            "not_comparable_inputs": not_comparable,
            "record_count": len(reports),
            "status": (
                "not_comparable"
                if not_comparable
                else "mismatch" if mismatch_count else "match"
            ),
            "summary": str(files.summary_path),
        }
    )
    if saw_unsupported:
        return EXIT_UNSUPPORTED
    if not_comparable:
        return EXIT_RUNNER
    return EXIT_MISMATCH if mismatch_count else EXIT_MATCH


def _verify_replay(args: argparse.Namespace) -> int:
    from .replay import load_failure_bundle, verify_replay_artifacts

    try:
        bundle = load_failure_bundle(args.failure)
    except ValidationError as exc:
        _print(
            {
                "reason": str(exc),
                "stage": "bundle_validation",
                "status": "invalid_bundle",
            }
        )
        return EXIT_SPECIFICATION

    try:
        intel_manifest = (
            args.intel
            if args.intel.is_absolute()
            else bundle.root / args.intel
        )
        openpower_manifest = (
            args.openpower
            if args.openpower.is_absolute()
            else bundle.root / args.openpower
        )
        verification, intel, power = verify_replay_artifacts(
            bundle,
            intel_manifest=intel_manifest,
            openpower_manifest=openpower_manifest,
        )
    except ValidationError as exc:
        _print(
            {
                "input_id": bundle.failure["input_id"],
                "reason": str(exc),
                "stage": "replay_result_validation",
                "status": "runner_error",
            }
        )
        return EXIT_RUNNER

    development_artifacts = (
        bundle.baseline_intel.development_fixture,
        bundle.baseline_openpower.development_fixture,
        intel.development_fixture,
        power.development_fixture,
    )
    if any(development_artifacts) and not args.allow_development_fixtures:
        _print(
            {
                "input_id": bundle.failure["input_id"],
                "reason": "development fixtures require --allow-development-fixtures",
                "status": "unsupported",
            }
        )
        return EXIT_UNSUPPORTED

    result: dict[str, JSONValue] = {
        "environment_differences": verification.environment_differences,
        "input_id": bundle.failure["input_id"],
        "replay_comparison": verification.replay_comparison,
        "result_differences": verification.result_differences,
        "status": "reproduced" if verification.reproduced else "not_reproduced",
    }
    _print(result)
    return EXIT_MATCH if verification.reproduced else EXIT_MISMATCH


def _add_contract_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--isa-registry", required=True, type=Path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ioitf",
        description="Intel Intrinsics / OpenPOWER equivalence-test coordinator",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    validate_cases = subcommands.add_parser("validate-cases")
    _add_contract_arguments(validate_cases)
    validate_cases.set_defaults(handler=_validate_cases)

    generate = subcommands.add_parser("generate-vectors")
    _add_contract_arguments(generate)
    generate.add_argument("--output", required=True, type=Path)
    generate.add_argument(
        "--profile",
        choices=("smoke", "standard", "exhaustive-small", "stress"),
        default="smoke",
    )
    generate.add_argument("--count-per-case", type=int)
    generate.add_argument("--seed", default=DEFAULT_SEED)
    generate.set_defaults(handler=_generate_vectors)

    validate = subcommands.add_parser("validate-artifact")
    _add_contract_arguments(validate)
    validate.add_argument("--kind", choices=("input", "result"), required=True)
    validate.add_argument("--manifest", required=True, type=Path)
    validate.add_argument("--input", type=Path)
    validate.set_defaults(handler=_validate_artifact)

    fixture = subcommands.add_parser("fixture-run")
    _add_contract_arguments(fixture)
    fixture.add_argument("--input", required=True, type=Path)
    fixture.add_argument("--role", choices=("intel", "openpower"), required=True)
    fixture.add_argument("--output", required=True, type=Path)
    fixture.add_argument(
        "--i-understand-this-is-not-native-evidence",
        action="store_true",
        dest="i_understand_this_is_not_native_evidence",
    )
    fixture.set_defaults(handler=_fixture_run)

    compare = subcommands.add_parser("compare-results")
    _add_contract_arguments(compare)
    compare.add_argument("--input", required=True, type=Path)
    compare.add_argument("--intel", required=True, type=Path)
    compare.add_argument("--openpower", required=True, type=Path)
    compare.add_argument("--output", required=True, type=Path)
    compare.add_argument("--allow-development-fixtures", action="store_true")
    compare.set_defaults(handler=_compare_results)

    verify_replay = subcommands.add_parser("verify-replay")
    verify_replay.add_argument("--failure", required=True, type=Path)
    verify_replay.add_argument("--intel", required=True, type=Path)
    verify_replay.add_argument("--openpower", required=True, type=Path)
    verify_replay.add_argument("--allow-development-fixtures", action="store_true")
    verify_replay.set_defaults(handler=_verify_replay)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return int(args.handler(args))
    except IOITFError as exc:
        print(f"ioitf: {exc}", file=sys.stderr)
        return exc.exit_code
    except OSError as exc:
        print(f"ioitf: operating-system error: {exc}", file=sys.stderr)
        return EXIT_RUNNER


if __name__ == "__main__":
    raise SystemExit(main())
