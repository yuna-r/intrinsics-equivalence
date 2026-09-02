"""Lightweight quality metrics and opt-in heavyweight quality gates."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable, Iterable

from .canonical import JSONValue, atomic_write, dump_bytes, loads
from .cases import CaseDefinition
from .development import load_development_case
from .errors import IOITFError


_PROGRESS_PREFIX = "IOITF_PROGRESS "


@dataclass(frozen=True)
class QualityMetrics:
    cases: int
    valid_contracts: int
    development_models: int
    standard_boundary_floors: int
    architecture_bindings: int


@dataclass(frozen=True)
class QualityRun:
    status: str
    report_path: Path
    passed_gates: int
    total_gates: int
    coverage_percent: str | None = None
    tests_run: int | None = None


@dataclass(frozen=True)
class QualityGateUpdate:
    gate: int
    gates: int
    label: str
    current: int
    total: int
    state: str = "running"


def collect_quality_metrics(cases: Iterable[CaseDefinition]) -> QualityMetrics:
    ordered = tuple(cases)
    models = 0
    boundary_floors = 0
    bindings = 0
    for case in ordered:
        development = load_development_case(case)
        models += 1
        if development.minimum_counts.get("standard", 0) > 0:
            boundary_floors += 1
        for role in ("intel", "openpower"):
            definition = case.data[role]
            if isinstance(definition, dict) and isinstance(definition.get("symbol"), str):
                bindings += 1
    return QualityMetrics(
        cases=len(ordered),
        valid_contracts=len(ordered),
        development_models=models,
        standard_boundary_floors=boundary_floors,
        architecture_bindings=bindings,
    )


def _write_log(path: Path, command: list[str], completed: subprocess.CompletedProcess[str]) -> None:
    rendered = "$ " + " ".join(command) + "\n"
    if completed.stdout:
        rendered += completed.stdout
        if not rendered.endswith("\n"):
            rendered += "\n"
    if completed.stderr:
        rendered += completed.stderr
        if not rendered.endswith("\n"):
            rendered += "\n"
    atomic_write(path, rendered.encode("utf-8"))


def _execute(
    command: list[str],
    *,
    root: Path,
    log: Path,
    progress: Callable[[int, int], None] | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if extra_env is not None:
        environment.update(extra_env)
    try:
        if progress is None:
            completed = subprocess.run(
                command,
                cwd=root,
                capture_output=True,
                check=False,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )
        else:
            process = subprocess.Popen(
                command,
                cwd=root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding="utf-8",
                errors="replace",
                env=environment,
            )
            lines: list[str] = []
            assert process.stdout is not None
            for line in process.stdout:
                lines.append(line)
                if line.startswith(_PROGRESS_PREFIX):
                    fields = line[len(_PROGRESS_PREFIX) :].split()
                    if len(fields) == 2:
                        try:
                            current, total = (int(field) for field in fields)
                        except ValueError:
                            continue
                        if total > 0 and 0 <= current <= total:
                            progress(current, total)
            process.stdout.close()
            return_code = process.wait()
            completed = subprocess.CompletedProcess(
                command, return_code, "".join(lines), ""
            )
    except OSError as exc:
        completed = subprocess.CompletedProcess(command, 127, "", str(exc))
    _write_log(log, command, completed)
    return completed


def _gate(status: str, log: Path, **details: JSONValue) -> dict[str, JSONValue]:
    return {"log": str(log), "status": status, **details}


def run_quality_gates(
    project_root: Path,
    output: Path,
    *,
    progress: Callable[[QualityGateUpdate], None] | None = None,
) -> QualityRun:
    """Run expensive checks only when the caller explicitly requests them."""

    root = project_root.resolve()
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    gates: dict[str, JSONValue] = {}

    coverage_output = output / "python-coverage"
    coverage_log = output / "python-coverage.log"
    coverage_command = [
        sys.executable,
        "-m",
        "ioitf.quality_runner",
        "--project-root",
        str(root),
        "--output",
        str(coverage_output),
    ]
    coverage_label = "Python tests + coverage"
    coverage_work = [0, 1]

    def coverage_progress(current: int, total: int) -> None:
        coverage_work[:] = [current, total]
        if progress is not None:
            progress(QualityGateUpdate(1, 3, coverage_label, current, total))

    if progress is not None:
        progress(QualityGateUpdate(1, 3, coverage_label, 0, 1))
    coverage_process = _execute(
        coverage_command,
        root=root,
        log=coverage_log,
        progress=coverage_progress,
    )
    coverage_details: dict[str, JSONValue] = {}
    if coverage_process.stdout.strip():
        try:
            parsed = loads(coverage_process.stdout.strip().splitlines()[-1])
        except (IOITFError, ValueError):
            parsed = None
        if isinstance(parsed, dict):
            coverage_details = {
                key: value
                for key, value in parsed.items()
                if key not in {"log", "status"}
            }
    coverage_status = "pass" if coverage_process.returncode == 0 else "failed"
    gates["python_coverage"] = _gate(
        "pass" if coverage_status == "pass" else "fail",
        coverage_log,
        **coverage_details,
    )
    if progress is not None:
        current, total = coverage_work
        if coverage_status == "pass":
            current = total
        progress(
            QualityGateUpdate(
                1, 3, coverage_label, current, total, coverage_status
            )
        )

    sanitizer_log = output / "sanitizers.log"
    sanitizer_build = output / "sanitizer-build"
    sanitizer_commands = (
        [
            "cmake",
            "-S",
            str(root),
            "-B",
            str(sanitizer_build),
            "-DBUILD_TESTING=ON",
            "-DIOITF_BUILD_NATIVE_ADAPTER=OFF",
            "-DCMAKE_BUILD_TYPE=Debug",
            "-DCMAKE_C_FLAGS=-fsanitize=address,undefined -fno-omit-frame-pointer",
            "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address,undefined",
            "-DCMAKE_SHARED_LINKER_FLAGS=-fsanitize=address,undefined",
        ],
        ["cmake", "--build", str(sanitizer_build), "--parallel"],
        ["ctest", "--test-dir", str(sanitizer_build), "--output-on-failure"],
    )
    sanitizer_label = "C sanitizers"
    if progress is not None:
        progress(QualityGateUpdate(2, 3, sanitizer_label, 0, 3))
    sanitizer_outputs: list[str] = []
    sanitizer_passed = True
    for command_index, command in enumerate(sanitizer_commands, start=1):
        part_log = output / f".sanitizer-{len(sanitizer_outputs)}.log"
        completed = _execute(command, root=root, log=part_log)
        sanitizer_outputs.append(part_log.read_text(encoding="utf-8"))
        part_log.unlink()
        if progress is not None:
            progress(
                QualityGateUpdate(
                    2, 3, sanitizer_label, command_index, len(sanitizer_commands)
                )
            )
        if completed.returncode != 0:
            sanitizer_passed = False
            break
    atomic_write(sanitizer_log, "".join(sanitizer_outputs).encode("utf-8"))
    gates["c_sanitizers"] = _gate(
        "pass" if sanitizer_passed else "fail", sanitizer_log
    )
    if progress is not None:
        progress(
            QualityGateUpdate(
                2,
                3,
                sanitizer_label,
                command_index,
                len(sanitizer_commands),
                "pass" if sanitizer_passed else "failed",
            )
        )

    cross_log = output / "cross-build.log"
    cross_script = root / "10_official_suite" / "cross-compile.sh"
    cross_command = [str(cross_script), str(output / "cross-build")]
    cross_label = "Intel + OpenPOWER cross build"
    cross_work = [0, 12]

    def cross_progress(current: int, total: int) -> None:
        cross_work[:] = [current, total]
        if progress is not None:
            progress(QualityGateUpdate(3, 3, cross_label, current, total))

    if progress is not None:
        progress(QualityGateUpdate(3, 3, cross_label, 0, 12))
    if cross_script.is_file():
        cross_process = _execute(
            cross_command,
            root=root,
            log=cross_log,
            progress=cross_progress,
            extra_env={"IOITF_PROGRESS": "1"},
        )
        cross_status = "pass" if cross_process.returncode == 0 else "fail"
    else:
        atomic_write(cross_log, b"cross-compile.sh was not found\n")
        cross_status = "fail"
    gates["cross_build"] = _gate(cross_status, cross_log)
    if progress is not None:
        current, total = cross_work
        if cross_status == "pass":
            current = total
        progress(
            QualityGateUpdate(
                3,
                3,
                cross_label,
                current,
                total,
                "pass" if cross_status == "pass" else "failed",
            )
        )

    passed = sum(
        1
        for value in gates.values()
        if isinstance(value, dict) and value.get("status") == "pass"
    )
    status = "pass" if passed == len(gates) else "fail"
    summary: dict[str, JSONValue] = {
        "gates": gates,
        "passed_gates": passed,
        "status": status,
        "total_gates": len(gates),
    }
    report = output / "summary.json"
    atomic_write(report, dump_bytes(summary, newline=True))
    coverage_percent = coverage_details.get("coverage_percent")
    tests_run = coverage_details.get("tests_run")
    return QualityRun(
        status,
        report,
        passed,
        len(gates),
        str(coverage_percent) if isinstance(coverage_percent, str) else None,
        (
            tests_run
            if isinstance(tests_run, int) and not isinstance(tests_run, bool)
            else None
        ),
    )
