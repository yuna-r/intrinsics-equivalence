from __future__ import annotations

import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from typing import Callable


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.artifacts import validate_input_artifact, validate_result_artifact  # noqa: E402
from ioitf.canonical import (  # noqa: E402
    JSONValue,
    atomic_write,
    dump_bytes,
    iter_canonical_jsonl,
    read_canonical_json,
    write_jsonl,
)
from ioitf.cases import load_case_definitions  # noqa: E402
from ioitf.cli import main  # noqa: E402
from ioitf.compare import compare_result_records  # noqa: E402
from ioitf.fixture import run_fixture  # noqa: E402
from ioitf.generator import generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402
from ioitf.report import write_failure_bundle  # noqa: E402


RecordMutation = Callable[[list[dict[str, JSONValue]]], None]


class ReplayVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa_path = PROJECT / "cases" / "isa-registry.json"
        cls.isa = load_isa_registry(cls.isa_path)
        cls.cases = load_case_definitions(PROJECT / "cases", isa_registry=cls.isa)

    def _rewrite_result(self, manifest_path: Path, mutation: RecordMutation) -> None:
        manifest = read_canonical_json(manifest_path)
        metadata = manifest["results"]
        assert isinstance(metadata, dict)
        results_path = manifest_path.parent / str(metadata["file"])
        records = list(iter_canonical_jsonl(results_path))
        mutation(records)
        count, byte_length, digest = write_jsonl(results_path, records)
        manifest["results"] = {
            "byte_length": byte_length,
            "file": results_path.name,
            "record_count": count,
            "sha256": digest,
        }
        atomic_write(manifest_path, dump_bytes(manifest, newline=True))

    @staticmethod
    def _set_first_return_lane(
        records: list[dict[str, JSONValue]], value: str
    ) -> None:
        observed = records[0]["observed"]
        assert isinstance(observed, dict)
        returned = observed["return"]
        assert isinstance(returned, dict)
        lanes = returned["lanes"]
        assert isinstance(lanes, list)
        lanes[0] = value

    def _make_failure_bundle(self, root: Path) -> Path:
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
            output=root / "baseline-source-intel",
        )
        power_run = run_fixture(
            input_artifact=inputs,
            cases=self.cases,
            isa_registry=self.isa,
            role="openpower",
            output=root / "baseline-source-power",
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

        first_input = inputs.records[0]
        input_id = str(first_input["input_id"])
        power_observed = power.records[input_id]["observed"]
        assert isinstance(power_observed, dict)
        power_return = power_observed["return"]
        assert isinstance(power_return, dict)
        power_lanes = power_return["lanes"]
        assert isinstance(power_lanes, list)
        faulty_lane = f"0x{int(str(power_lanes[0]), 16) ^ 1:016x}"
        self._rewrite_result(
            power_run.manifest_path,
            lambda records: self._set_first_return_lane(records, faulty_lane),
        )
        faulty_power = validate_result_artifact(
            power_run.manifest_path,
            self.cases,
            self.isa,
            input_artifact=inputs,
        )
        case = self.cases.get(str(first_input["case_id"]))
        comparison = compare_result_records(
            case,
            first_input,
            intel.records[input_id],
            faulty_power.records[input_id],
            validate=False,
        )
        self.assertEqual(comparison.outcome, "mismatch")
        return write_failure_bundle(
            output=root / "comparison",
            input_artifact=inputs,
            intel_artifact=intel,
            openpower_artifact=faulty_power,
            cases=self.cases,
            isa_registry=self.isa,
            input_record=first_input,
            comparison=comparison,
        )

    def _make_replay_results(
        self, bundle: Path, *, reproduce: bool
    ) -> tuple[Path, Path]:
        bundle_cases = load_case_definitions(
            bundle / "contracts" / "case-definitions.json",
            isa_registry=self.isa,
        )
        bundle_input = validate_input_artifact(
            bundle / "test-vectors.manifest.json", bundle_cases, self.isa
        )
        intel_run = run_fixture(
            input_artifact=bundle_input,
            cases=bundle_cases,
            isa_registry=self.isa,
            role="intel",
            output=bundle / "replay" / "intel",
        )
        power_run = run_fixture(
            input_artifact=bundle_input,
            cases=bundle_cases,
            isa_registry=self.isa,
            role="openpower",
            output=bundle / "replay" / "openpower",
        )

        self._rewrite_result(
            intel_run.manifest_path,
            lambda records: records[0].__setitem__("duration_ns", 101),
        )
        if reproduce:
            baseline = validate_result_artifact(
                bundle / "baseline" / "openpower" / "power-results.manifest.json",
                bundle_cases,
                self.isa,
                input_artifact=bundle_input,
            )
            input_id = str(bundle_input.records[0]["input_id"])
            observed = baseline.records[input_id]["observed"]
            assert isinstance(observed, dict)
            returned = observed["return"]
            assert isinstance(returned, dict)
            lanes = returned["lanes"]
            assert isinstance(lanes, list)
            expected_lane = str(lanes[0])

            def reproduce_power(records: list[dict[str, JSONValue]]) -> None:
                records[0]["duration_ns"] = 202
                self._set_first_return_lane(records, expected_lane)

            self._rewrite_result(power_run.manifest_path, reproduce_power)
        else:
            self._rewrite_result(
                power_run.manifest_path,
                lambda records: records[0].__setitem__("duration_ns", 202),
            )
        return intel_run.manifest_path, power_run.manifest_path

    @staticmethod
    def _verify(
        bundle: Path,
        intel: Path,
        power: Path,
        *,
        allow_development_fixtures: bool = True,
    ) -> tuple[int, str, str]:
        arguments = [
            "verify-replay",
            "--failure",
            str(bundle / "failure.json"),
            "--intel",
            str(intel),
            "--openpower",
            str(power),
        ]
        if allow_development_fixtures:
            arguments.append("--allow-development-fixtures")
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            exit_code = main(arguments)
        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_relative_replay_paths_are_resolved_from_failure_not_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            unrelated_cwd = root / "unrelated-cwd"
            unrelated_cwd.mkdir()
            original_cwd = Path.cwd()
            try:
                os.chdir(unrelated_cwd)
                exit_code, stdout, stderr = self._verify(
                    bundle,
                    intel.relative_to(bundle),
                    power.relative_to(bundle),
                )
            finally:
                os.chdir(original_cwd)
            self.assertEqual(exit_code, 0, stderr)
            self.assertIn('"status":"reproduced"', stdout)

    def test_changed_replay_result_is_not_reproduced(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=False)
            exit_code, stdout, stderr = self._verify(bundle, intel, power)
            self.assertEqual(exit_code, 1, stderr)
            self.assertIn('"status":"not_reproduced"', stdout)

    def test_tampered_failure_metadata_is_an_invalid_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            failure_path = bundle / "failure.json"
            failure = read_canonical_json(failure_path)
            failure["mismatch_count"] = int(failure["mismatch_count"]) + 1
            atomic_write(failure_path, dump_bytes(failure, newline=True))
            exit_code, stdout, stderr = self._verify(bundle, intel, power)
            self.assertEqual(exit_code, 2, stdout + stderr)
            self.assertIn("invalid_bundle", stdout + stderr)

    def test_failure_schema_is_closed_and_paths_and_commands_are_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            failure_path = bundle / "failure.json"
            original = read_canonical_json(failure_path)

            def unknown_nested_key(value: dict[str, JSONValue]) -> None:
                baseline = value["baseline"]
                assert isinstance(baseline, dict)
                baseline["extra"] = "not-allowed"

            def nonfixed_path(value: dict[str, JSONValue]) -> None:
                contracts = value["contracts"]
                assert isinstance(contracts, dict)
                cases = contracts["case_definitions"]
                assert isinstance(cases, dict)
                cases["file"] = "../case-definitions.json"

            def changed_command(value: dict[str, JSONValue]) -> None:
                reproduce = value["reproduce"]
                assert isinstance(reproduce, dict)
                verify = reproduce["verify"]
                assert isinstance(verify, list)
                verify[0], verify[1] = verify[1], verify[0]

            mutations = {
                "unknown nested key": unknown_nested_key,
                "nonfixed path": nonfixed_path,
                "changed command ordering": changed_command,
            }
            for name, mutation in mutations.items():
                with self.subTest(name=name):
                    changed = copy.deepcopy(original)
                    mutation(changed)
                    atomic_write(failure_path, dump_bytes(changed, newline=True))
                    exit_code, stdout, stderr = self._verify(bundle, intel, power)
                    self.assertEqual(exit_code, 2, stdout + stderr)
                    self.assertIn("invalid_bundle", stdout + stderr)
            atomic_write(failure_path, dump_bytes(original, newline=True))

    def test_development_fixture_replays_require_explicit_permission(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            exit_code, stdout, stderr = self._verify(
                bundle,
                intel,
                power,
                allow_development_fixtures=False,
            )
            self.assertEqual(exit_code, 3, stdout + stderr)
            self.assertIn("unsupported", stdout + stderr)

    def test_corrupt_replay_result_is_a_runner_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            power_manifest = read_canonical_json(power)
            metadata = power_manifest["results"]
            assert isinstance(metadata, dict)
            results_path = power.parent / str(metadata["file"])
            with results_path.open("ab") as stream:
                stream.write(b" ")
            exit_code, stdout, stderr = self._verify(bundle, intel, power)
            self.assertEqual(exit_code, 4, stdout + stderr)
            self.assertIn("runner_error", stdout + stderr)

    def test_environment_differences_are_diagnostic_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            manifest = read_canonical_json(intel)
            runner = manifest["runner"]
            environment = manifest["environment"]
            assert isinstance(runner, dict) and isinstance(environment, dict)
            runner["build_id"] = "development-fixture:intel:python-v2"
            environment["cpu_model"] = "replay-cpu-model"
            atomic_write(intel, dump_bytes(manifest, newline=True))

            exit_code, stdout, stderr = self._verify(bundle, intel, power)
            self.assertEqual(exit_code, 0, stderr)
            self.assertIn('"status":"reproduced"', stdout)
            self.assertIn('"runner.build_id"', stdout)
            self.assertIn('"environment.cpu_model"', stdout)

    def test_required_bundle_file_cannot_be_a_symlink_outside_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = self._make_failure_bundle(root)
            intel, power = self._make_replay_results(bundle, reproduce=True)
            vectors = bundle / "test-vectors.jsonl"
            outside = root / "outside-test-vectors.jsonl"
            outside.write_bytes(vectors.read_bytes())
            vectors.unlink()
            vectors.symlink_to(outside)

            exit_code, stdout, stderr = self._verify(bundle, intel, power)
            self.assertEqual(exit_code, 2, stdout + stderr)
            self.assertIn("invalid_bundle", stdout + stderr)


if __name__ == "__main__":
    unittest.main()
