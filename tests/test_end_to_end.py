from __future__ import annotations

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
from ioitf.cli import main  # noqa: E402
from ioitf.compare import compare_result_records  # noqa: E402
from ioitf.fixture import run_fixture  # noqa: E402
from ioitf.generator import generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402
from ioitf.records import derive_input_id  # noqa: E402
from ioitf.report import RecordReport, write_failure_bundle, write_reports  # noqa: E402


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa_path = PROJECT / "contracts" / "isa-registry.json"
        cls.suite_path = PROJECT / "examples" / "sse2"
        cls.isa = load_isa_registry(cls.isa_path)
        cls.cases = load_case_definitions(cls.suite_path, isa_registry=cls.isa)

    def test_one_command_development_check(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "check"
            stdout = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(io.StringIO()):
                exit_code = main(
                    [
                        "check",
                        "--project", str(PROJECT / "ioitf.toml"),
                        "--output", str(output),
                        "--count-per-case", "2",
                    ]
                )
            self.assertEqual(exit_code, 0)
            result = loads(stdout.getvalue().strip())
            assert isinstance(result, dict)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(result["native_evidence"])
            self.assertEqual(result["record_count"], 6)
            self.assertTrue((output / "comparison" / "summary.json").is_file())

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
            lanes[0] = f"0x{int(str(lanes[0]), 16) ^ 1:016x}"
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
            shutil.copyfile(source.parent / "development.py", root / "development.py")
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
