"""Isolated regression and source-line coverage runner for ``--quality``.

This module runs in a child process so the ordinary ``ioitf check`` path never
pays tracing overhead.  It intentionally uses only the Python standard library.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import redirect_stdout
import io
from pathlib import Path
import platform
import sys
import trace
import unittest

from .canonical import JSONValue, atomic_write, dump_bytes, dumps, sha256_file
from .oracle import ModelOutputMismatch


_PROGRESS_PREFIX = "IOITF_PROGRESS "


def _emit_progress(current: int, total: int) -> None:
    print(f"{_PROGRESS_PREFIX}{current} {total}", flush=True)


class _ProgressResult(unittest.TextTestResult):
    def __init__(
        self,
        stream: unittest.runner._WritelnDecorator,  # type: ignore[name-defined]
        descriptions: bool,
        verbosity: int,
        *,
        total: int,
    ) -> None:
        super().__init__(stream, descriptions, verbosity)
        self._completed = 0
        self._total = total
        self.model_oracle_tests_run = 0
        self.model_oracle_checks_run = 0
        self.model_oracle_reference: JSONValue = None
        self.model_output_mismatches: list[JSONValue] = []

    def startTest(self, test: unittest.TestCase) -> None:
        super().startTest(test)
        if getattr(test, "verification_subject", None) == "portable_model_oracle":
            self.model_oracle_tests_run += 1
            reference = getattr(test, "oracle_reference_metadata", None)
            if reference is not None:
                self.model_oracle_reference = reference

    def _record_model_mismatch(self, test: unittest.TestCase, err: tuple) -> None:
        if isinstance(err[1], ModelOutputMismatch):
            self.model_output_mismatches.append({
                **err[1].evidence, "test_id": test.id(),
            })

    def addFailure(self, test: unittest.TestCase, err: tuple) -> None:
        self._record_model_mismatch(test, err)
        super().addFailure(test, err)

    def addSubTest(self, test: unittest.TestCase, subtest: unittest.TestCase,
                   err: tuple | None) -> None:
        if err is not None:
            self._record_model_mismatch(subtest, err)
        super().addSubTest(test, subtest, err)

    def stopTest(self, test: unittest.case.TestCase) -> None:
        super().stopTest(test)
        self.model_oracle_checks_run += getattr(test, "oracle_checks", 0)
        self._completed += 1
        _emit_progress(self._completed, self._total)


class _ProgressRunner(unittest.TextTestRunner):
    def __init__(self, *args: object, total: int, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._total = total

    def _makeResult(self) -> unittest.TextTestResult:
        return _ProgressResult(
            self.stream,
            self.descriptions,
            self.verbosity,
            total=self._total,
        )


def _run_tests(
    tests: Path, stream: io.StringIO
) -> tuple[_ProgressResult, int]:
    suite = unittest.TestLoader().discover(str(tests), pattern="test_*.py")
    total = suite.countTestCases() + 1
    _emit_progress(0, total)
    result = _ProgressRunner(stream=stream, verbosity=2, total=total).run(suite)
    return result, total


def _coverage_totals(
    source: Path, counts: dict[tuple[str, int], int]
) -> tuple[int, int, int]:
    covered_lines = 0
    executable_lines = 0
    source_files = 0
    resolved_counts = {
        (str(Path(filename).resolve()), line): count
        for (filename, line), count in counts.items()
    }
    for path in sorted(source.rglob("*.py")):
        if path.name == "quality_runner.py":
            continue
        source_files += 1
        executable = set(trace._find_executable_linenos(str(path)))  # type: ignore[attr-defined]
        executable.discard(0)
        executable_lines += len(executable)
        resolved = str(path.resolve())
        covered_lines += sum(
            1 for line in executable if resolved_counts.get((resolved, line), 0) > 0
        )
    return source_files, covered_lines, executable_lines


def _source_counts(
    source: Path, counts: dict[tuple[str, int], int]
) -> dict[tuple[str, int], int]:
    root = source.resolve()
    selected: dict[tuple[str, int], int] = {}
    for (filename, line), count in counts.items():
        path = Path(filename).resolve()
        if path.name != "quality_runner.py" and path.is_relative_to(root):
            selected[(str(path), line)] = count
    return selected


def run(project_root: Path, output: Path) -> tuple[int, dict[str, JSONValue]]:
    source = project_root / "src" / "ioitf"
    tests = project_root / "tests"
    if not source.is_dir() or not tests.is_dir():
        raise RuntimeError("quality coverage requires src/ioitf and tests directories")

    output.mkdir(parents=True, exist_ok=False)
    test_log = io.StringIO()
    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=[sys.base_prefix, sys.prefix],
    )
    result, progress_total = tracer.runfunc(_run_tests, tests, test_log)
    coverage = tracer.results()
    coverage.counts = _source_counts(source, coverage.counts)

    rendered_summary = io.StringIO()
    with redirect_stdout(rendered_summary):
        coverage.write_results(
            show_missing=True,
            summary=True,
            coverdir=str(output / "annotated"),
        )
    atomic_write(output / "tests.log", test_log.getvalue().encode("utf-8"))
    atomic_write(
        output / "coverage-summary.txt",
        rendered_summary.getvalue().encode("utf-8"),
    )

    source_files, covered_lines, executable_lines = _coverage_totals(
        source, coverage.counts
    )
    _emit_progress(progress_total, progress_total)
    coverage_percent = (
        "100"
        if executable_lines == 0
        else f"{covered_lines * 100 / executable_lines:.1f}".rstrip("0").rstrip(".")
    )
    summary: dict[str, JSONValue] = {
        "coverage_percent": coverage_percent,
        "covered_lines": covered_lines,
        "errors": len(result.errors),
        "executable_lines": executable_lines,
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "source_files": source_files,
        "status": "pass" if result.wasSuccessful() else "fail",
        "tests_run": result.testsRun,
        "failure_classification": {
            "portable_model_output_mismatches": len(result.model_output_mismatches),
            "other_assertion_failures": len(result.failures) - len(result.model_output_mismatches),
            "test_execution_errors": len(result.errors),
        },
        "model_oracle_tests_run": result.model_oracle_tests_run,
        "model_oracle_checks_run": result.model_oracle_checks_run,
        "model_oracle_reference": result.model_oracle_reference,
        "model_findings_by_family": dict(Counter(
            row["finding_family"] for row in result.model_output_mismatches
        )),
        "model_findings_by_contract_scope": dict(Counter(
            row["contract_scope"] for row in result.model_output_mismatches
        )),
        "model_output_mismatches": result.model_output_mismatches,
        "execution_environment": {
            "machine": platform.machine(),
            "system": platform.system(),
            "python_version": platform.python_version(),
        },
        "evidence_sources": {
            str(path.relative_to(project_root)): sha256_file(path)
            for path in (
                tests / "test_adversarial_models.py",
                tests / "data" / "rounding-oracles.json",
                tests / "native" / "probe_sse2_nan.c",
                tests / "build_rounding_oracles.py",
                source / "casepack_families.py",
                source / "oracle.py",
            ) if path.is_file()
        },
    }
    atomic_write(output / "summary.json", dump_bytes(summary, newline=True))
    return (0 if result.wasSuccessful() else 1), summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        exit_code, summary = run(args.project_root.resolve(), args.output.resolve())
    except (OSError, RuntimeError) as exc:
        print(f"ioitf quality coverage: {exc}", file=sys.stderr)
        return 1
    print(dumps(summary))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
