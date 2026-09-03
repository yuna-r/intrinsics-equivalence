from __future__ import annotations

import argparse
import copy
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.artifacts import validate_input_artifact, validate_result_artifact  # noqa: E402
from ioitf.canonical import (  # noqa: E402
    atomic_write,
    dump_bytes,
    loads,
    read_canonical_json,
    write_jsonl,
)
from ioitf.cases import load_case_definitions  # noqa: E402
from ioitf.cli import (  # noqa: E402
    _CheckProgress,
    _QualityGateProgress,
    _parse_jobs,
    main,
)
from ioitf.compare import compare_result_records  # noqa: E402
from ioitf.fixture import run_fixture  # noqa: E402
from ioitf.generator import generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402
from ioitf.records import derive_input_id  # noqa: E402
from ioitf.report import RecordReport, write_failure_bundle, write_reports  # noqa: E402
from ioitf.quality import QualityGateUpdate, QualityRun  # noqa: E402


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa_path = PROJECT / "contracts" / "isa-registry.json"
        cls.suite_path = PROJECT / "10_official_suite" / "cases"
        cls.isa = load_isa_registry(cls.isa_path)
        cls.cases = load_case_definitions(cls.suite_path, isa_registry=cls.isa)

    def test_one_command_development_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "check"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "check",
                        "--project", str(PROJECT / "ioitf.toml"),
                        "--output", str(output),
                        "--count-per-case", "2",
                        "--showcase-report",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = loads(stdout.getvalue().strip())
            assert isinstance(result, dict)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(result["native_evidence"])
            self.assertEqual(result["record_count"], 352)
            self.assertTrue((output / "comparison" / "summary.json").is_file())
            self.assertEqual(result["showcase_report"], str(output / "showcase.html"))
            showcase = (output / "showcase.html").read_text(encoding="utf-8")
            self.assertIn("COHERENCE CONFIRMED", showcase)
            self.assertIn("sse2.shuffle.i32x4.imm8", showcase)
            self.assertIn("DEVELOPMENT SIMULATION", showcase)
            progress = stderr.getvalue()
            self.assertIn("[1/7] Prepare suite...", progress)
            self.assertIn("[2/7] Generate test vectors: done", progress)
            self.assertIn("[3/7] Run Intel fixture: done", progress)
            self.assertIn("[4/7] Run OpenPOWER fixture: done", progress)
            self.assertIn("[5/7] Validate + compare results: done", progress)
            self.assertIn("[6/7] Build showcase report: done", progress)
            self.assertIn("[7/7] PASS - 352 trials: done", progress)
            self.assertIn("Verification metrics", progress)
            self.assertRegex(progress, r"cases\s+176")
            self.assertRegex(progress, r"trials\s+352")
            self.assertRegex(progress, r"implementation-path evaluations\s+704")
            self.assertRegex(progress, r"lane verdicts\s+1,812")
            self.assertRegex(progress, r"bit positions\s+42,816")
            self.assertRegex(progress, r"match rate\s+100%")
            self.assertRegex(progress, r"mismatch\s+0")
            self.assertIn("Quality metrics", progress)
            self.assertRegex(progress, r"valid contracts\s+176 / 176")
            self.assertRegex(progress, r"portable models\s+176 / 176")
            self.assertRegex(progress, r"architecture bindings\s+352 / 352")

    def test_check_prints_metrics_without_showcase_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "plain-check"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "check",
                        "--project", str(PROJECT / "ioitf.toml"),
                        "--output", str(output),
                        "--count-per-case", "1",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = loads(stdout.getvalue().strip())
            assert isinstance(result, dict)
            self.assertNotIn("showcase_report", result)
            metrics = stderr.getvalue()
            self.assertIn("Verification metrics", metrics)
            self.assertRegex(metrics, r"cases\s+176")
            self.assertRegex(metrics, r"trials\s+176")
            self.assertRegex(metrics, r"implementation-path evaluations\s+352")
            self.assertRegex(metrics, r"lane verdicts\s+906")
            self.assertRegex(metrics, r"bit positions\s+21,408")
            self.assertRegex(metrics, r"match rate\s+100%")
            self.assertRegex(metrics, r"mismatch\s+0")
            self.assertIn("Quality metrics", metrics)

    def test_parallel_check_is_byte_identical_to_serial_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            outputs = {"serial": root / "serial", "parallel": root / "parallel"}
            results: dict[str, dict[str, object]] = {}
            for name, jobs in (("serial", "1"), ("parallel", "2")):
                stdout = io.StringIO()
                with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                    exit_code = main(
                        [
                            "check",
                            "--project", str(PROJECT / "ioitf.toml"),
                            "--output", str(outputs[name]),
                            "--count-per-case", "1",
                            "--jobs", jobs,
                            "--quiet",
                        ]
                    )
                self.assertEqual(exit_code, 0)
                parsed = loads(stdout.getvalue().strip())
                assert isinstance(parsed, dict)
                results[name] = parsed

            self.assertEqual(results["serial"]["jobs"], 1)
            self.assertEqual(results["parallel"]["jobs"], 2)
            for relative in (
                "vectors/test-vectors.jsonl",
                "intel/intel-results.jsonl",
                "intel/intel-results.manifest.json",
                "openpower/power-results.jsonl",
                "openpower/power-results.manifest.json",
                "comparison/summary.json",
                "comparison/junit.xml",
            ):
                self.assertEqual(
                    (outputs["serial"] / relative).read_bytes(),
                    (outputs["parallel"] / relative).read_bytes(),
                    relative,
                )

    def test_jobs_accepts_auto_and_rejects_nonpositive_values(self) -> None:
        with mock.patch("ioitf.cli.os.cpu_count", return_value=12):
            self.assertEqual(_parse_jobs("auto"), 12)
        self.assertEqual(_parse_jobs("3"), 3)
        with self.assertRaisesRegex(argparse.ArgumentTypeError, "at least 1"):
            _parse_jobs("0")

    def test_quality_option_is_an_eighth_opt_in_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "quality-check"
            report = output / "quality" / "summary.json"
            stdout = io.StringIO()
            stderr = io.StringIO()
            deep = QualityRun("pass", report, 3, 3, "87.5", 82)
            with mock.patch("ioitf.cli.run_quality_gates", return_value=deep):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    exit_code = main(
                        [
                            "check",
                            "--project", str(PROJECT / "ioitf.toml"),
                            "--output", str(output),
                            "--count-per-case", "1",
                            "--quality",
                        ]
                    )
            self.assertEqual(exit_code, 0)
            result = loads(stdout.getvalue().strip())
            assert isinstance(result, dict)
            self.assertEqual(result["quality_status"], "pass")
            self.assertEqual(result["quality_report"], str(report))
            progress = stderr.getvalue()
            self.assertIn("[7/8] Run quality gates", progress)
            self.assertIn("[8/8] PASS - 176 trials", progress)
            self.assertRegex(progress, r"regression tests\s+82 passed")
            self.assertRegex(progress, r"source line coverage\s+87.5%")
            self.assertRegex(progress, r"deep quality gates\s+3 / 3")

    def test_check_quiet_keeps_stderr_empty_and_stdout_canonical(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "quiet-check"
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "check",
                        "--project", str(PROJECT / "ioitf.toml"),
                        "--output", str(output),
                        "--count-per-case", "2",
                        "--quiet",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = loads(stdout.getvalue().strip())
            assert isinstance(result, dict)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(stderr.getvalue(), "")

    def test_interactive_progress_updates_one_terminal_line(self) -> None:
        class TTYBuffer(io.StringIO):
            def isatty(self) -> bool:
                return True

        stream = TTYBuffer()
        progress = _CheckProgress(enabled=True, stream=stream)
        with progress.stage(2, "Generate test vectors", total=4) as update:
            update(1)
            update(4)

        rendered = stream.getvalue()
        self.assertIn("\r[2/7] Generate test vectors", rendered)
        self.assertIn("[======================] 100% 4/4", rendered)
        self.assertIn("done", rendered)

    def test_interactive_progress_can_name_quality_substages(self) -> None:
        class TTYBuffer(io.StringIO):
            def isatty(self) -> bool:
                return True

        stream = TTYBuffer()
        progress = _CheckProgress(enabled=True, steps=8, stream=stream)
        with progress.stage(7, "Run quality gates"):
            progress.open_details()
            gates = _QualityGateProgress(
                enabled=True, interactive=True, stream=stream
            )
            gates.update(QualityGateUpdate(1, 3, "Python tests + coverage", 0, 84))
            gates.update(QualityGateUpdate(1, 3, "Python tests + coverage", 84, 84, "pass"))
            gates.update(QualityGateUpdate(2, 3, "C sanitizers", 0, 3))
            gates.update(QualityGateUpdate(2, 3, "C sanitizers", 3, 3, "pass"))
            gates.update(QualityGateUpdate(3, 3, "Intel + OpenPOWER cross build", 0, 12))
            gates.update(QualityGateUpdate(3, 3, "Intel + OpenPOWER cross build", 12, 12, "pass"))

        rendered = stream.getvalue()
        self.assertIn("[7/8] Run quality gates\n", rendered)
        self.assertIn("[1/3] Python tests + coverage", rendered)
        self.assertIn("[2/3] C sanitizers", rendered)
        self.assertIn("[3/3] Intel + OpenPOWER cross build", rendered)
        self.assertEqual(rendered.count("PASS"), 3)
        self.assertEqual(rendered.count("100%"), 3)
        self.assertTrue(rendered.endswith("\n"))

    def test_fixture_match_tamper_detection_and_failure_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "vectors",
                count_per_case=4,
            )
            inputs = validate_input_artifact(generated.manifest_path, self.cases, self.isa)
            intel_run = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            power_run = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="openpower",
                output=root / "power",
            )
            intel = validate_result_artifact(
                intel_run.manifest_path,
                self.cases,
                self.isa,
                input_artifact=inputs,
            )
            power = validate_result_artifact(
                power_run.manifest_path,
                self.cases,
                self.isa,
                input_artifact=inputs,
            )
            for input_record in inputs.records:
                input_id = str(input_record["input_id"])
                comparison = compare_result_records(
                    self.cases.get(str(input_record["case_id"])),
                    input_record,
                    intel.records[input_id],
                    power.records[input_id],
                    validate=False,
                )
                self.assertEqual(comparison.outcome, "match")

            # A development fixture is unusable unless the caller explicitly opts in.
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(
                    [
                        "compare-results",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--intel", str(intel_run.manifest_path),
                        "--openpower", str(power_run.manifest_path),
                        "--output", str(root / "forbidden"),
                    ]
                )
            self.assertEqual(exit_code, 3)

            stale_output = root / "stale-comparison"
            atomic_write(
                stale_output / "reference-error.json",
                dump_bytes({"stale": True}, newline=True),
            )
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                stale_exit = main(
                    [
                        "compare-results",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--intel", str(intel_run.manifest_path),
                        "--openpower", str(power_run.manifest_path),
                        "--output", str(stale_output),
                        "--allow-development-fixtures",
                    ]
                )
            self.assertEqual(stale_exit, 2)
            self.assertFalse((stale_output / "summary.json").exists())

            first_input = inputs.records[0]
            first_id = str(first_input["input_id"])
            modified_records = copy.deepcopy(list(power.ordered_records))
            modified = modified_records[0]
            observed = modified["observed"]
            assert isinstance(observed, dict)
            returned = observed["return"]
            assert isinstance(returned, dict)
            lanes = returned["lanes"]
            assert isinstance(lanes, list)
            original_lane = str(lanes[0])
            lane_width = len(original_lane) - 2
            lanes[0] = f"0x{int(original_lane, 16) ^ 1:0{lane_width}x}"
            count, byte_length, digest = write_jsonl(power.results_path, modified_records)
            manifest = copy.deepcopy(power.manifest)
            manifest["results"] = {
                "byte_length": byte_length,
                "file": "power-results.jsonl",
                "record_count": count,
                "sha256": digest,
            }
            atomic_write(power.manifest_path, dump_bytes(manifest, newline=True))
            modified_power = validate_result_artifact(
                power.manifest_path,
                self.cases,
                self.isa,
                input_artifact=inputs,
            )
            comparison = compare_result_records(
                self.cases.get(str(first_input["case_id"])),
                first_input,
                intel.records[first_id],
                modified_power.records[first_id],
                validate=False,
            )
            self.assertEqual(comparison.outcome, "mismatch")
            self.assertEqual(comparison.mismatch_count, 1)
            self.assertEqual(comparison.first_difference["kind"], "return")
            self.assertEqual(comparison.first_difference["lane"], 0)

            output = root / "comparison"
            bundle = write_failure_bundle(
                output=output,
                input_artifact=inputs,
                intel_artifact=intel,
                openpower_artifact=modified_power,
                cases=self.cases,
                isa_registry=self.isa,
                input_record=first_input,
                comparison=comparison,
            )
            failure = read_canonical_json(bundle / "failure.json")
            self.assertEqual(failure["input_id"], first_id)
            self.assertEqual(failure["mismatch_count"], 1)
            self.assertTrue((bundle / "baseline/intel/intel-results.manifest.json").is_file())
            self.assertTrue((bundle / "baseline/openpower/power-results.manifest.json").is_file())

            files = write_reports(
                output,
                [
                    RecordReport(
                        str(first_input["case_id"]),
                        first_id,
                        comparison,
                        str(bundle.relative_to(output) / "failure.json"),
                    )
                ],
            )
            summary = read_canonical_json(files.summary_path)
            self.assertEqual(summary["outcome"], "mismatch")
            self.assertEqual(summary["mismatch_atoms"], 1)
            self.assertIn("<failure", files.junit_path.read_text(encoding="utf-8"))

    def test_unsupported_status_difference_bundles_and_exits_three(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "vectors",
                count_per_case=1,
            )
            inputs = validate_input_artifact(generated.manifest_path, self.cases, self.isa)
            intel_run = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            power_run = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="openpower",
                output=root / "power",
            )
            power = validate_result_artifact(
                power_run.manifest_path,
                self.cases,
                self.isa,
                input_artifact=inputs,
            )
            records = copy.deepcopy(list(power.ordered_records))
            records[0].pop("observed")
            records[0]["error"] = {
                "code": "development_capability_unavailable",
                "stage": "capability",
            }
            records[0]["status"] = "unsupported"
            count, byte_length, digest = write_jsonl(power.results_path, records)
            manifest = copy.deepcopy(power.manifest)
            manifest["results"] = {
                "byte_length": byte_length,
                "file": "power-results.jsonl",
                "record_count": count,
                "sha256": digest,
            }
            atomic_write(power.manifest_path, dump_bytes(manifest, newline=True))

            output = root / "comparison"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(
                    [
                        "compare-results",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--intel", str(intel_run.manifest_path),
                        "--openpower", str(power_run.manifest_path),
                        "--output", str(output),
                        "--allow-development-fixtures",
                    ]
                )
            self.assertEqual(exit_code, 3)
            first_id = str(inputs.records[0]["input_id"])
            failure_path = output / "failures" / first_id / "failure.json"
            self.assertTrue(failure_path.is_file())
            failure = read_canonical_json(failure_path)
            self.assertEqual(failure["first_difference"]["kind"], "status")

    def test_compare_classifies_corrupt_result_as_runner_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            generated = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "vectors",
                count_per_case=1,
            )
            inputs = validate_input_artifact(generated.manifest_path, self.cases, self.isa)
            intel = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            power = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="openpower",
                output=root / "power",
            )
            with power.results_path.open("ab") as stream:
                stream.write(b" ")
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(
                    [
                        "compare-results",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--intel", str(intel.manifest_path),
                        "--openpower", str(power.manifest_path),
                        "--output", str(root / "comparison"),
                        "--allow-development-fixtures",
                    ]
                )
            self.assertEqual(exit_code, 4)
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                validation_exit = main(
                    [
                        "validate-artifact",
                        "--kind", "result",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--manifest", str(power.manifest_path),
                    ]
                )
            self.assertEqual(validation_exit, 4)

    def test_output_filesystem_failure_is_reported_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_file = Path(temporary) / "not-a-directory"
            output_file.write_text("occupied", encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stdout(io.StringIO()), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "generate-vectors",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--output", str(output_file),
                        "--count-per-case", "1",
                    ]
                )
            self.assertEqual(exit_code, 4)
            self.assertIn("operating-system error", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_atomic_publication_failure_is_a_runner_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stderr = io.StringIO()
            with (
                mock.patch(
                    "ioitf.canonical.os.replace",
                    side_effect=PermissionError("publication denied"),
                ),
                redirect_stdout(io.StringIO()),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "generate-vectors",
                        "--cases", str(self.suite_path),
                        "--isa-registry", str(self.isa_path),
                        "--output", str(Path(temporary) / "vectors"),
                        "--count-per-case", "1",
                    ]
                )
            self.assertEqual(exit_code, 4)
            self.assertIn("cannot publish", stderr.getvalue())

    def test_rounding_witness_must_differ_from_nearest_even_on_intel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = copy.deepcopy(self.cases.get("sse2.set1.f64x2.default").data)
            data["environment"]["fp_rounding_modes"] = [
                "nearest_even",
                "toward_zero",
            ]
            identity = {
                "case_id": data["id"],
                "environment": {"fp_mode": "ieee", "rounding": "toward_zero"},
                "operands": {
                    "value": {"bits": "0x8000000000000000", "element": "f64"}
                },
            }
            data["regressions"] = {
                "ineffective-rounding-witness.v1": {
                    "expected_intel": {
                        "observed": {
                            "return": {
                                "element": "f64",
                                "lanes": [
                                    "0x8000000000000000",
                                    "0x8000000000000000",
                                ],
                            }
                        },
                        "status": "ok",
                    },
                    "input_id": derive_input_id(identity),
                }
            }
            case_path = root / "case.json"
            atomic_write(case_path, dump_bytes(data, newline=True))
            source = self.cases.get(data["id"]).source_path
            assert source is not None
            shutil.copyfile(source, root / "development.py")
            registry = load_case_definitions(case_path, isa_registry=self.isa)
            generated = generate_artifact(
                cases=registry,
                isa_registry=self.isa,
                output=root / "vectors",
                count_per_case=3,
            )
            inputs = validate_input_artifact(generated.manifest_path, registry, self.isa)
            intel = run_fixture(
                input_artifact=inputs,
                cases=registry,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            power = run_fixture(
                input_artifact=inputs,
                cases=registry,
                isa_registry=self.isa,
                role="openpower",
                output=root / "power",
            )
            output = root / "comparison"
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                exit_code = main(
                    [
                        "compare-results",
                        "--cases", str(case_path),
                        "--isa-registry", str(self.isa_path),
                        "--input", str(generated.manifest_path),
                        "--intel", str(intel.manifest_path),
                        "--openpower", str(power.manifest_path),
                        "--output", str(output),
                        "--allow-development-fixtures",
                    ]
                )
            self.assertEqual(exit_code, 5)
            self.assertTrue((output / "reference-error.json").is_file())
            self.assertFalse((output / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
