from __future__ import annotations

from pathlib import Path
import copy
import sys
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.artifacts import (  # noqa: E402
    validate_input_artifact,
    validate_result_artifact,
)
from ioitf.canonical import (  # noqa: E402
    atomic_write,
    dump_bytes,
    iter_canonical_jsonl,
    read_canonical_json,
    write_jsonl,
)
from ioitf.cases import load_case_definitions  # noqa: E402
from ioitf.errors import ValidationError  # noqa: E402
from ioitf.fixture import run_fixture  # noqa: E402
from ioitf.generator import generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry  # noqa: E402


class ArtifactValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
        cls.cases = load_case_definitions(
            PROJECT / "10_official_suite" / "cases", isa_registry=cls.isa
        )

    def _input(self, root: Path):
        generated = generate_artifact(
            cases=self.cases,
            isa_registry=self.isa,
            output=root / "vectors",
            profile="smoke",
            count_per_case=2,
        )
        return validate_input_artifact(generated.manifest_path, self.cases, self.isa)

    def test_input_manifest_file_and_projection_are_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            artifact = self._input(root)
            self.assertEqual(artifact.record_count, 192)
            self.assertEqual(len(artifact.records), 192)
            self.assertEqual(artifact.case_ids, self.cases.ids)
            self.assertTrue(artifact.isa_registry_matches_local)

            manifest = read_canonical_json(artifact.manifest_path)
            manifest["case_definitions_sha256"] = "0" * 64
            atomic_write(artifact.manifest_path, dump_bytes(manifest, newline=True))
            with self.assertRaisesRegex(ValidationError, "projection SHA-256 mismatch"):
                validate_input_artifact(artifact.manifest_path, self.cases, self.isa)

    def test_input_data_tampering_is_rejected_before_records_are_trusted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            artifact = self._input(Path(temporary))
            with artifact.vectors_path.open("ab") as stream:
                stream.write(b" ")
            with self.assertRaisesRegex(ValidationError, "byte length mismatch"):
                validate_input_artifact(artifact.manifest_path, self.cases, self.isa)

    def test_result_relationship_and_development_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self._input(root)
            fixture = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            result = validate_result_artifact(
                fixture.manifest_path,
                self.cases,
                self.isa,
                input_artifact=inputs,
            )
            self.assertEqual(result.role, "intel")
            self.assertTrue(result.development_fixture)
            self.assertEqual(set(result.records), {str(row["input_id"]) for row in inputs.records})

    def test_result_with_unknown_input_id_is_rejected_even_when_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self._input(root)
            fixture = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            records = list(iter_canonical_jsonl(fixture.results_path))
            records[0]["input_id"] = "f" * 64
            count, byte_length, digest = write_jsonl(fixture.results_path, records)
            manifest = read_canonical_json(fixture.manifest_path)
            results = manifest["results"]
            assert isinstance(results, dict)
            results.update(
                {"byte_length": byte_length, "record_count": count, "sha256": digest}
            )
            atomic_write(fixture.manifest_path, dump_bytes(manifest, newline=True))
            with self.assertRaisesRegex(ValidationError, "unknown input_id"):
                validate_result_artifact(
                    fixture.manifest_path,
                    self.cases,
                    self.isa,
                    input_artifact=inputs,
                )

    def test_huge_probe_version_suffix_is_a_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = self._input(root)
            fixture = run_fixture(
                input_artifact=inputs,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            manifest = copy.deepcopy(read_canonical_json(fixture.manifest_path))
            preflight = manifest["preflight"]
            assert isinstance(preflight, dict)
            suite = preflight["probe_suite"]
            assert isinstance(suite, list) and isinstance(suite[0], dict)
            suite[0]["id"] = "fixture-controls.v" + "9" * 5000
            atomic_write(fixture.manifest_path, dump_bytes(manifest, newline=True))
            with self.assertRaisesRegex(ValidationError, "ID and version disagree"):
                validate_result_artifact(
                    fixture.manifest_path,
                    self.cases,
                    self.isa,
                    input_artifact=inputs,
                )

    def test_result_validation_uses_the_captured_input_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "vectors",
                profile="smoke",
                count_per_case=17,
                seed="0x0000000000000001",
            )
            captured = validate_input_artifact(first.manifest_path, self.cases, self.isa)

            second = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "vectors",
                profile="smoke",
                count_per_case=17,
                seed="0x0000000000000002",
            )
            replacement = validate_input_artifact(second.manifest_path, self.cases, self.isa)
            self.assertNotEqual(captured.sha256, replacement.sha256)
            fixture = run_fixture(
                input_artifact=replacement,
                cases=self.cases,
                isa_registry=self.isa,
                role="intel",
                output=root / "intel",
            )
            with self.assertRaisesRegex(ValidationError, "input SHA-256"):
                validate_result_artifact(
                    fixture.manifest_path,
                    self.cases,
                    self.isa,
                    input_artifact=captured,
                )


if __name__ == "__main__":
    unittest.main()
