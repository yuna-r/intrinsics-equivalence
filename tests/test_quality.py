from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.canonical import read_canonical_json  # noqa: E402
from ioitf.cases import load_case_definitions  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402
from ioitf.quality import (  # noqa: E402
    QualityGateUpdate,
    _execute,
    collect_quality_metrics,
    run_quality_gates,
)
from ioitf.quality_runner import (  # noqa: E402
    _coverage_totals,
    _source_counts,
    run as run_coverage,
)


class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
        cls.cases = load_case_definitions(
            PROJECT / "10_official_suite" / "cases", isa_registry=isa
        )

    def test_light_metrics_cover_every_case_without_running_heavy_gates(self) -> None:
        metrics = collect_quality_metrics(self.cases)
        self.assertEqual(metrics.cases, 128)
        self.assertEqual(metrics.valid_contracts, 128)
        self.assertEqual(metrics.development_models, 128)
        self.assertEqual(metrics.standard_boundary_floors, 128)
        self.assertEqual(metrics.architecture_bindings, 256)

    def test_coverage_totals_include_unexecuted_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary)
            covered = source / "covered.py"
            missing = source / "missing.py"
            covered.write_text("def value():\n    return 42\n", encoding="utf-8")
            missing.write_text("def other():\n    return 7\n", encoding="utf-8")
            files, hit, executable = _coverage_totals(
                source, {(str(covered.resolve()), 1): 1, (str(covered.resolve()), 2): 1}
            )
            self.assertEqual(files, 2)
            self.assertEqual(hit, 2)
            self.assertGreater(executable, hit)

    def test_coverage_annotations_ignore_deleted_temporary_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "ioitf"
            source.mkdir(parents=True)
            kept = source / "kept.py"
            transient = root / "already-deleted.py"
            kept.write_text("value = 1\n", encoding="utf-8")
            counts = {
                (str(kept), 1): 1,
                (str(transient), 1): 1,
            }
            self.assertEqual(
                _source_counts(source, counts), {(str(kept.resolve()), 1): 1}
            )

    def test_command_progress_markers_are_streamed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            log = Path(temporary) / "command.log"
            updates: list[tuple[int, int]] = []
            completed = _execute(
                [
                    sys.executable,
                    "-c",
                    (
                        "print('IOITF_PROGRESS 1 2', flush=True); "
                        "print('IOITF_PROGRESS 2 2', flush=True)"
                    ),
                ],
                root=PROJECT,
                log=log,
                progress=lambda current, total: updates.append((current, total)),
            )
            self.assertEqual(completed.returncode, 0)
            self.assertEqual(updates, [(1, 2), (2, 2)])
            self.assertIn("IOITF_PROGRESS 2 2", log.read_text(encoding="utf-8"))

    def test_coverage_runner_reports_tests_and_final_coverage_step(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "src" / "ioitf"
            tests = root / "tests"
            source.mkdir(parents=True)
            tests.mkdir()
            (source / "sample.py").write_text(
                "def answer():\n    return 42\n", encoding="utf-8"
            )
            (tests / "test_sample.py").write_text(
                (
                    "import unittest\n\n"
                    "class SampleTest(unittest.TestCase):\n"
                    "    def test_answer(self):\n"
                    "        self.assertEqual(42, 42)\n"
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code, summary = run_coverage(root, root / "coverage")

            self.assertEqual(exit_code, 0)
            self.assertEqual(summary["tests_run"], 1)
            markers = [
                line for line in output.getvalue().splitlines()
                if line.startswith("IOITF_PROGRESS ")
            ]
            self.assertEqual(
                markers,
                [
                    "IOITF_PROGRESS 0 2",
                    "IOITF_PROGRESS 1 2",
                    "IOITF_PROGRESS 2 2",
                ],
            )

    def test_deep_gates_write_one_summary_and_three_logs(self) -> None:
        coverage = (
            '{"coverage_percent":"87.5","covered_lines":700,"errors":0,'
            '"executable_lines":800,"failures":0,"skipped":0,'
            '"source_files":20,"status":"pass","tests_run":80}\n'
        )
        completed = [
            subprocess.CompletedProcess([], 0, coverage, ""),
            subprocess.CompletedProcess([], 0, "configured\n", ""),
            subprocess.CompletedProcess([], 0, "built\n", ""),
            subprocess.CompletedProcess([], 0, "tests passed\n", ""),
            subprocess.CompletedProcess([], 0, "cross passed\n", ""),
        ]
        completed_results = iter(completed)

        def execute_stub(
            command: list[str], *, root: Path, log: Path, **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            result = next(completed_results)
            log.write_text(result.stdout, encoding="utf-8")
            return result

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "project"
            output = Path(temporary) / "quality"
            script = root / "10_official_suite" / "cross-compile.sh"
            script.parent.mkdir(parents=True)
            script.write_text("#!/bin/sh\n", encoding="utf-8")
            progress: list[QualityGateUpdate] = []
            with mock.patch("ioitf.quality._execute", side_effect=execute_stub):
                result = run_quality_gates(
                    root,
                    output,
                    progress=progress.append,
                )

            self.assertEqual(result.status, "pass")
            self.assertEqual((result.passed_gates, result.total_gates), (3, 3))
            self.assertEqual(result.coverage_percent, "87.5")
            self.assertEqual(result.tests_run, 80)
            self.assertEqual(progress[0].current, 0)
            self.assertEqual(progress[0].state, "running")
            self.assertEqual(progress[1].current, progress[1].total)
            self.assertEqual(progress[1].state, "pass")
            sanitizer = [update for update in progress if update.gate == 2]
            self.assertEqual(
                [update.current for update in sanitizer], [0, 1, 2, 3, 3]
            )
            self.assertEqual(sanitizer[-1].state, "pass")
            self.assertEqual(progress[-1].gate, 3)
            self.assertEqual(progress[-1].current, progress[-1].total)
            self.assertEqual(progress[-1].state, "pass")
            summary = read_canonical_json(result.report_path)
            self.assertEqual(summary["status"], "pass")
            gates = summary["gates"]
            assert isinstance(gates, dict)
            python = gates["python_coverage"]
            assert isinstance(python, dict)
            self.assertEqual(python["coverage_percent"], "87.5")
            self.assertTrue((output / "python-coverage.log").is_file())
            self.assertTrue((output / "sanitizers.log").is_file())
            self.assertTrue((output / "cross-build.log").is_file())


if __name__ == "__main__":
    unittest.main()
