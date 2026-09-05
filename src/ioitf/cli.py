"""Command-line coordinator for IOITF artifacts."""

from __future__ import annotations

import argparse
from contextlib import contextmanager, redirect_stdout
import copy
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import sys
import time
from typing import Callable, Iterator, Sequence, TextIO

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
from .generator import DEFAULT_SEED, PROFILE_COUNTS, generate_artifact
from .isa import ISARegistry, load_isa_registry
from .metrics import VerificationMetrics, collect_verification_metrics
from .project import load_project
from .quality import (
    QualityGateUpdate,
    QualityMetrics,
    QualityRun,
    collect_quality_metrics,
    run_quality_gates,
)
from .records import derive_input_id


def _parse_jobs(value: str) -> int:
    if value == "auto":
        return max(1, os.cpu_count() or 1)
    try:
        jobs = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("jobs must be a positive integer or 'auto'") from exc
    if jobs < 1:
        raise argparse.ArgumentTypeError("jobs must be at least 1")
    return jobs


def _contract_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    cases_path = args.cases
    isa_path = args.isa_registry
    if cases_path is None or isa_path is None:
        project = load_project(args.project)
        cases_path = project.suite if cases_path is None else cases_path
        isa_path = project.isa_registry if isa_path is None else isa_path
    return cases_path, isa_path


def _contracts(args: argparse.Namespace) -> tuple[CaseRegistry, ISARegistry]:
    cases_path, isa_path = _contract_paths(args)
    isa = load_isa_registry(isa_path)
    cases = load_case_definitions(cases_path, isa_registry=isa)
    return cases, isa


def _print(value: JSONValue) -> None:
    print(dumps(value))


def _print_verification_metrics(
    metrics: VerificationMetrics, *, stream: TextIO | None = None
) -> None:
    destination = sys.stderr if stream is None else stream
    rate = f"{metrics.match_rate:.2f}".rstrip("0").rstrip(".") + "%"
    rows = (
        ("cases", f"{metrics.case_count:,}"),
        ("trials", f"{metrics.trials:,}"),
        (
            "implementation-path evaluations",
            f"{metrics.implementation_path_evaluations:,}",
        ),
        ("lane verdicts", f"{metrics.lane_verdicts:,}"),
        ("bit positions", f"{metrics.bit_positions:,}"),
        ("match rate", rate),
        ("mismatch", f"{metrics.mismatched_inputs:,}"),
    )
    width = max(len(label) for label, _value in rows)
    print("\nVerification metrics", file=destination)
    for label, value in rows:
        print(f"  {label:<{width}}  {value:>12}", file=destination)
    destination.flush()


def _print_quality_metrics(
    metrics: QualityMetrics,
    *,
    deep: QualityRun | None = None,
    stream: TextIO | None = None,
) -> None:
    destination = sys.stderr if stream is None else stream
    bindings = metrics.cases * 2
    rows = [
        ("valid contracts", f"{metrics.valid_contracts:,} / {metrics.cases:,}"),
        ("portable models", f"{metrics.development_models:,} / {metrics.cases:,}"),
        (
            "standard boundary floors",
            f"{metrics.standard_boundary_floors:,} / {metrics.cases:,}",
        ),
        (
            "architecture bindings",
            f"{metrics.architecture_bindings:,} / {bindings:,}",
        ),
        ("contract drift", "0"),
    ]
    if deep is not None:
        if deep.tests_run is not None:
            rows.append(("regression tests", f"{deep.tests_run:,} executed"))
        if deep.coverage_percent is not None:
            rows.append(("source line coverage", deep.coverage_percent + "%"))
        rows.append(
            ("deep quality gates", f"{deep.passed_gates:,} / {deep.total_gates:,}")
        )
    width = max(len(label) for label, _value in rows)
    print("\nQuality metrics", file=destination)
    for label, value in rows:
        print(f"  {label:<{width}}  {value:>12}", file=destination)
    destination.flush()


class _CheckProgress:
    """Small dependency-free progress display that leaves stdout machine-readable."""

    _BAR_WIDTH = 22

    def __init__(
        self,
        *,
        enabled: bool,
        steps: int = 7,
        stream: TextIO | None = None,
    ):
        self.enabled = enabled
        self.steps = steps
        self.stream = sys.stderr if stream is None else stream
        isatty = getattr(self.stream, "isatty", None)
        self.interactive = bool(isatty is not None and isatty())
        self._step = 0
        self._label = ""
        self._total: int | None = None
        self._current = 0
        self._last_percent = -1
        self._last_width = 0
        self._started = 0.0

    @contextmanager
    def stage(
        self, step: int, label: str, *, total: int | None = None
    ) -> Iterator[Callable[[int], None]]:
        if not self.enabled:
            yield lambda _current: None
            return
        self._step = step
        self._label = label
        self._total = total
        self._current = 0
        self._last_percent = -1
        self._started = time.monotonic()
        if self.interactive:
            self._render(force=True)
        else:
            print(f"[{step}/{self.steps}] {label}...", file=self.stream, flush=True)
        try:
            yield self.update
        except BaseException:
            self._finish(success=False)
            raise
        else:
            self._finish(success=True)

    def update(self, current: int) -> None:
        if not self.enabled or self._total is None:
            return
        self._current = max(0, min(current, self._total))
        if self.interactive:
            self._render()

    def open_details(self) -> None:
        """Move nested progress below the current interactive stage line."""

        if not self.enabled or not self.interactive:
            return
        self._render(force=True)
        self.stream.write("\n")
        self.stream.flush()
        self._last_width = 0

    def _format_line(self) -> str:
        prefix = f"[{self._step}/{self.steps}] {self._label:<25}"
        if self._total is None:
            return prefix.rstrip()
        percent = 100 if self._total == 0 else self._current * 100 // self._total
        filled = percent * self._BAR_WIDTH // 100
        bar = "=" * filled + "-" * (self._BAR_WIDTH - filled)
        return (
            f"{prefix} [{bar}] {percent:3d}% "
            f"{self._current:,}/{self._total:,}"
        )

    def _render(self, *, force: bool = False) -> None:
        if self._total is not None:
            percent = 100 if self._total == 0 else self._current * 100 // self._total
            if not force and percent == self._last_percent:
                return
            self._last_percent = percent
        line = self._format_line()
        self.stream.write("\r" + line.ljust(self._last_width))
        self.stream.flush()
        self._last_width = max(self._last_width, len(line))

    def _finish(self, *, success: bool) -> None:
        elapsed = time.monotonic() - self._started
        if success and self._total is not None:
            self._current = self._total
        suffix = f"  {'done' if success else 'failed'} {elapsed:.1f}s"
        if self.interactive:
            line = self._format_line() + suffix
            self.stream.write("\r" + line.ljust(self._last_width) + "\n")
            self.stream.flush()
            self._last_width = 0
            return
        state = "done" if success else "failed"
        print(
            f"[{self._step}/{self.steps}] {self._label}: {state} ({elapsed:.1f}s)",
            file=self.stream,
            flush=True,
        )


class _QualityGateProgress:
    """Three persistent child rows for the opt-in quality gates."""

    def __init__(
        self,
        *,
        enabled: bool,
        interactive: bool,
        stream: TextIO,
    ) -> None:
        self.enabled = enabled
        self.interactive = interactive
        self.stream = stream
        self._active_width = 0
        self._started: dict[int, float] = {}
        self._last_percent: dict[int, int] = {}

    def update(self, update: QualityGateUpdate) -> None:
        if not self.enabled:
            return
        if update.gate not in self._started:
            self._started[update.gate] = time.monotonic()
        percent = (
            100
            if update.total == 0
            else min(100, update.current * 100 // update.total)
        )
        filled = percent * 18 // 100
        bar = "=" * filled + "-" * (18 - filled)
        suffix = ""
        if update.state != "running":
            elapsed = time.monotonic() - self._started[update.gate]
            suffix = f"  {update.state.upper()} ({elapsed:.1f}s)"
        line = (
            f"  [{update.gate}/{update.gates}] {update.label:<36} "
            f"[{bar}] {percent:3d}% "
            f"{update.current:,}/{update.total:,}{suffix}"
        )
        if self.interactive:
            padding = " " * max(0, self._active_width - len(line))
            if update.state == "running":
                self.stream.write(("\r" if self._active_width else "") + line + padding)
                self._active_width = max(self._active_width, len(line))
            else:
                self.stream.write("\r" + line + padding + "\n")
                self._active_width = 0
            self.stream.flush()
            return
        last_percent = self._last_percent.get(update.gate, -10)
        if (
            update.state != "running"
            or percent == 0
            or percent == 100
            or percent >= last_percent + 10
        ):
            print(line, file=self.stream, flush=True)
            self._last_percent[update.gate] = percent

    def close(self) -> None:
        if self.enabled and self.interactive and self._active_width:
            self.stream.write("\n")
            self.stream.flush()
            self._active_width = 0


def _validate_cases(args: argparse.Namespace) -> int:
    cases_path, isa_path = _contract_paths(args)
    isa = load_isa_registry(isa_path)
    cases = load_case_definitions(cases_path, isa_registry=isa)
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
    cases_path, isa_path = _contract_paths(args)
    isa = load_isa_registry(isa_path)
    cases = load_case_definitions(cases_path, isa_registry=isa)
    result = generate_artifact(
        cases=cases,
        isa_registry=isa,
        output=args.output,
        profile=args.profile,
        count_per_case=args.count_per_case,
        seed=args.seed,
        jobs=args.jobs,
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
        jobs=args.jobs,
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
    from .compare import compare_result_record_set
    from .report import RecordReport, write_failure_bundle, write_reports

    validated_context = getattr(args, "validated_context", None)
    if validated_context is None:
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
    else:
        cases, isa, input_artifact, intel_artifact, power_artifact = validated_context
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
    progress = getattr(args, "progress", None)
    comparisons = compare_result_record_set(
        cases=cases,
        input_records=input_artifact.records,
        intel_records=intel_artifact.records,
        openpower_records=power_artifact.records,
        jobs=getattr(args, "jobs", 1),
        progress=progress,
    )
    for input_record, comparison in zip(input_artifact.records, comparisons):
        input_id = str(input_record["input_id"])
        intel_record = intel_artifact.records[input_id]
        power_record = power_artifact.records[input_id]
        saw_unsupported = saw_unsupported or (
            intel_record["status"] == "unsupported"
            or power_record["status"] == "unsupported"
        )
        case = cases.get(str(input_record["case_id"]))
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


def _development_check(args: argparse.Namespace) -> int:
    """Run the complete non-native authoring loop with one command."""

    from .fixture import run_fixture

    started_at = datetime.now(timezone.utc)
    progress = _CheckProgress(enabled=not args.quiet, steps=8 if args.quality else 7)
    with progress.stage(1, "Prepare suite"):
        cases_path, isa_path = _contract_paths(args)
        isa = load_isa_registry(isa_path)
        cases = load_case_definitions(cases_path, isa_registry=isa)
        if args.output is None:
            stamp = started_at.strftime("%Y%m%dT%H%M%S%fZ")
            output = Path(".ioitf") / "checks" / stamp
        else:
            output = args.output
        if output.exists():
            raise ValidationError(
                f"check output already exists; choose a fresh path: {output}"
            )

    requested_count = (
        PROFILE_COUNTS[args.profile]
        if args.count_per_case is None
        else args.count_per_case
    )
    expected_records = (
        len(cases) * requested_count if requested_count > 0 else None
    )
    with progress.stage(
        2, "Generate test vectors", total=expected_records
    ) as update:
        generated = generate_artifact(
            cases=cases,
            isa_registry=isa,
            output=output / "vectors",
            profile=args.profile,
            count_per_case=args.count_per_case,
            seed=args.seed,
            jobs=args.jobs,
            progress=update,
            retain_records=True,
        )
        inputs = generated.as_validated_artifact()

    with progress.stage(
        3, "Run Intel fixture", total=generated.record_count
    ) as update:
        intel = run_fixture(
            input_artifact=inputs,
            cases=cases,
            isa_registry=isa,
            role="intel",
            output=output / "intel",
            jobs=args.jobs,
            progress=update,
        )
        intel_artifact = intel.as_validated_artifact()

    with progress.stage(
        4, "Run OpenPOWER fixture", total=generated.record_count
    ) as update:
        openpower = run_fixture(
            input_artifact=inputs,
            cases=cases,
            isa_registry=isa,
            role="openpower",
            output=output / "openpower",
            jobs=args.jobs,
            progress=update,
        )
        openpower_artifact = openpower.as_validated_artifact()

    comparison = output / "comparison"
    with progress.stage(
        5, "Validate + compare results", total=generated.record_count
    ) as update:
        compare_args = argparse.Namespace(
            allow_development_fixtures=True,
            cases=cases_path,
            input=generated.manifest_path,
            intel=intel.manifest_path,
            isa_registry=isa_path,
            openpower=openpower.manifest_path,
            output=comparison,
            progress=update,
            jobs=args.jobs,
            validated_context=(
                cases,
                isa,
                inputs,
                intel_artifact,
                openpower_artifact,
            ),
        )
        with redirect_stdout(io.StringIO()):
            exit_code = _compare_results(compare_args)

    report_label = (
        "Build showcase report" if args.showcase_report and not args.quality else "Finalize artifacts"
    )
    with progress.stage(6, report_label):
        from .canonical import read_canonical_json

        summary = read_canonical_json(comparison / "summary.json")
        assert isinstance(summary, dict)
        metrics = collect_verification_metrics(cases, summary)
        result: dict[str, JSONValue] = {
            "artifacts": str(output),
            "case_count": len(cases),
            "development_fixture": True,
            "jobs": args.jobs,
            "native_evidence": False,
            "record_count": generated.record_count,
            "status": summary["outcome"],
        }
        def build_showcase(quality: dict[str, JSONValue] | None = None) -> None:
            from .showcase import write_showcase_report

            showcase = write_showcase_report(
                output / "showcase.html",
                cases=cases,
                summary=summary,
                profile=args.profile,
                seed=args.seed,
                vector_sha256=generated.sha256,
                case_definitions_sha256=generated.case_definitions_sha256,
                isa_contract_sha256=generated.used_isa_contract.sha256,
                generated_at=started_at,
                native_evidence=False,
                quality=quality,
            )
            result["showcase_report"] = str(showcase)

        if args.showcase_report and not args.quality:
            build_showcase()

    quality_metrics = collect_quality_metrics(cases)
    quality_run: QualityRun | None = None
    if args.quality:
        with progress.stage(7, "Run quality gates"):
            project_root = Path(args.project).resolve().parent
            progress.open_details()
            gate_progress = _QualityGateProgress(
                enabled=progress.enabled,
                interactive=progress.interactive,
                stream=progress.stream,
            )
            try:
                quality_run = run_quality_gates(
                    project_root,
                    output / "quality",
                    jobs=args.jobs,
                    progress=gate_progress.update,
                )
            finally:
                gate_progress.close()
            result["quality_report"] = str(quality_run.report_path)
            result["quality_status"] = quality_run.status
            if quality_run.status != "pass":
                result["status"] = "quality_failed"

    status = str(summary["outcome"]).upper()
    if quality_run is not None and quality_run.status != "pass":
        status = "QUALITY FAILED"
    final_step = 8 if args.quality else 7
    with progress.stage(final_step, f"{status} - {generated.record_count:,} trials"):
        if args.showcase_report and quality_run is not None:
            quality_summary = read_canonical_json(quality_run.report_path)
            assert isinstance(quality_summary, dict)
            build_showcase(quality_summary)
    if not args.quiet:
        _print_verification_metrics(metrics)
        _print_quality_metrics(quality_metrics, deep=quality_run)
    _print(result)
    if quality_run is not None and quality_run.status != "pass" and exit_code == EXIT_MATCH:
        return EXIT_MISMATCH
    return exit_code


def _add_contract_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--project",
        default=Path("ioitf.toml"),
        type=Path,
        help="project file used when suite paths are not explicitly supplied",
    )
    parser.add_argument("--cases", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--isa-registry", type=Path, help=argparse.SUPPRESS)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ioitf",
        description="Intel Intrinsics / OpenPOWER equivalence-test coordinator",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    check = subcommands.add_parser(
        "check",
        help="run the complete development-only authoring loop",
    )
    _add_contract_arguments(check)
    check.add_argument("--output", type=Path)
    check.add_argument(
        "--profile",
        choices=("smoke", "standard", "exhaustive-small", "stress"),
        default="smoke",
    )
    check.add_argument("--count-per-case", type=int, default=8)
    check.add_argument("--seed", default=DEFAULT_SEED)
    check.add_argument(
        "-j",
        "--jobs",
        default=1,
        type=_parse_jobs,
        help="case-level worker processes (positive integer or 'auto')",
    )
    check.add_argument(
        "--showcase-report",
        action="store_true",
        help="write a self-contained presentation-style HTML report",
    )
    check.add_argument(
        "--quality",
        action="store_true",
        help="run opt-in coverage, sanitizer, and cross-build quality gates",
    )
    check.add_argument(
        "--quiet",
        action="store_true",
        help="suppress progress on stderr; final JSON still goes to stdout",
    )
    check.set_defaults(handler=_development_check)

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
    generate.add_argument(
        "-j", "--jobs", default=1, type=_parse_jobs,
        help="case-level worker processes (positive integer or 'auto')",
    )
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
        "-j", "--jobs", default=1, type=_parse_jobs,
        help="case-level worker processes (positive integer or 'auto')",
    )
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
    compare.add_argument(
        "-j", "--jobs", default=1, type=_parse_jobs,
        help="case-level worker processes (positive integer or 'auto')",
    )
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
