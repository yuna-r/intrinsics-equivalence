from __future__ import annotations

import sys
from pathlib import Path
import copy
import shutil
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.canonical import (  # noqa: E402
    atomic_write,
    dump_bytes,
    iter_canonical_jsonl,
    read_canonical_json,
    sha256_file,
)
from ioitf.cases import load_case_definitions, validate_case_definition  # noqa: E402
from ioitf.errors import ValidationError  # noqa: E402
from ioitf.generator import SplitMix64, generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry, project_used_isa  # noqa: E402
from ioitf.records import derive_input_id  # noqa: E402


class CaseAndGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
        cls.cases = load_case_definitions(
            PROJECT / "examples" / "sse2", isa_registry=cls.isa
        )

    def test_registry_and_used_projection(self) -> None:
        self.assertEqual(
            self.cases.ids,
            (
                "sse2.add.f64x2.default",
                "sse2.set1.f64x2.default",
                "sse2.shuffle.i32x4.imm8",
            ),
        )
        used = project_used_isa(self.isa, self.cases)
        self.assertEqual(
            [token["token"] for token in used.data["tokens"]],
            ["power8", "sse2", "vsx"],
        )

    def test_case_contracts_are_yaml_case_packs(self) -> None:
        for case in self.cases:
            self.assertIsNotNone(case.source_path)
            assert case.source_path is not None
            self.assertEqual(case.source_path.name, "case.yaml")
            self.assertTrue((case.source_path.parent / "development.py").is_file())

    def test_yaml_rejects_duplicate_keys_aliases_and_non_json_scalars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.yaml"
            duplicate.write_text(
                "schema_version: 1\nid: one\nid: two\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValidationError, "duplicate mapping key"):
                load_case_definitions(duplicate, isa_registry=self.isa)

            alias = root / "alias.yaml"
            alias.write_text(
                "schema_version: 1\ntags: &shared []\ncopy: *shared\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "anchors and aliases"):
                load_case_definitions(alias, isa_registry=self.isa)

            original = self.cases.get("sse2.set1.f64x2.default").source_path
            assert original is not None
            non_json_bool = root / "non-json-bool.yaml"
            non_json_bool.write_text(
                original.read_text(encoding="utf-8").replace(
                    "observe_fp_exceptions: false", "observe_fp_exceptions: yes"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "expected a boolean"):
                load_case_definitions(non_json_bool, isa_registry=self.isa)

            float_number = root / "float.yaml"
            float_number.write_text(
                original.read_text(encoding="utf-8").replace(
                    "schema_version: 1", "schema_version: 1.0"
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValidationError, "floating-point"):
                load_case_definitions(float_number, isa_registry=self.isa)

    def test_generation_is_reproducible_and_manifest_is_last_marker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "one",
                profile="smoke",
                count_per_case=5,
            )
            second = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=root / "two",
                profile="smoke",
                count_per_case=5,
            )
            self.assertEqual(first.record_count, 15)
            self.assertEqual(first.sha256, second.sha256)
            self.assertEqual(first.vectors_path.read_bytes(), second.vectors_path.read_bytes())
            manifest = read_canonical_json(first.manifest_path)
            vectors = manifest["test_vectors"]
            self.assertIsInstance(vectors, dict)
            assert isinstance(vectors, dict)
            self.assertEqual(vectors["sha256"], sha256_file(first.vectors_path))
            lines = first.vectors_path.read_text(encoding="utf-8").splitlines()
            for line in lines:
                from ioitf.canonical import loads

                record = loads(line)
                self.assertIsInstance(record, dict)
                assert isinstance(record, dict)
                self.assertEqual(record["input_id"], derive_input_id(record))

    def test_input_id_does_not_include_sequence_or_generation(self) -> None:
        record = {
            "case_id": "example.case",
            "environment": {"fp_mode": "ieee", "rounding": "nearest_even"},
            "generation": {"class": "structured"},
            "input_id": "0" * 64,
            "operands": {"a": {"bits": "0x00", "element": "u8"}},
            "schema_version": 1,
            "sequence": 1,
        }
        first = derive_input_id(record)
        record["sequence"] = 99
        record["generation"] = {"class": "boundary"}
        self.assertEqual(first, derive_input_id(record))

    def test_regression_expected_observed_is_a_closed_typed_schema(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.set1.f64x2.default").data)
        data["regressions"] = {
            "closed-schema.v1": {
                "expected_intel": {"observed": {"nonsense": 123}, "status": "ok"},
                "input_id": "0" * 64,
            }
        }
        with self.assertRaisesRegex(ValidationError, "missing keys|unknown keys"):
            validate_case_definition(data, isa_registry=self.isa)

        expected = data["regressions"]["closed-schema.v1"]["expected_intel"]
        expected["observed"] = {
            "return": {
                "element": "f64",
                "lanes": ["0x0000000000000000", "0x0000000000000000"],
            }
        }
        validate_case_definition(data, isa_registry=self.isa)

    def test_u64_tolerance_rejects_huge_decimal_without_raw_value_error(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.add.f64x2.default").data)
        data["comparison"] = {
            "max_ulps": "9" * 5000,
            "mode": "ulp",
            "nan": {
                "both_nan": "equal",
                "payload": "ignore",
                "quiet_signaling": "ignore",
                "sign": "ignore",
            },
            "signed_zero": "equal",
        }
        with self.assertRaisesRegex(ValidationError, "canonical u64"):
            validate_case_definition(data, isa_registry=self.isa)

    def test_endianness_sensitive_operations_require_the_tag(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.shuffle.i32x4.imm8").data)
        data["tags"] = []
        with self.assertRaisesRegex(ValidationError, "endianness-sensitive"):
            validate_case_definition(data, isa_registry=self.isa)

    def test_nondefault_rounding_requires_a_regression(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.set1.f64x2.default").data)
        data["environment"]["fp_rounding_modes"] = ["nearest_even", "toward_zero"]
        with self.assertRaisesRegex(ValidationError, "regressions"):
            validate_case_definition(data, isa_registry=self.isa)

    def test_registered_rounding_witness_is_promoted_and_materialized(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.add.f64x2.default").data)
        data["environment"]["fp_rounding_modes"] = ["nearest_even", "toward_zero"]
        identity = {
            "case_id": data["id"],
            "environment": {"fp_mode": "ieee", "rounding": "toward_zero"},
            "operands": {
                "a": {
                    "element": "f64",
                    "lanes": ["0x3ff0000000000000", "0x3ff0000000000000"],
                },
                "b": {
                    "element": "f64",
                    "lanes": ["0x3ca8000000000000", "0x3ca8000000000000"],
                },
            },
        }
        regression_id = "rounding-toward-zero.v1"
        data["regressions"] = {
            regression_id: {
                "expected_intel": {
                    "observed": {
                        "return": {
                            "element": "f64",
                            "lanes": [
                                "0x3ff0000000000000",
                                "0x3ff0000000000000",
                            ],
                        }
                    },
                    "status": "ok",
                },
                "input_id": derive_input_id(identity),
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
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
                profile="smoke",
                count_per_case=9,
            )
            rows = list(iter_canonical_jsonl(generated.vectors_path))
            self.assertEqual(rows[7]["generation"], {
                "class": "regression",
                "regression_id": regression_id,
            })
            self.assertEqual(rows[7]["environment"]["rounding"], "toward_zero")
            self.assertEqual(rows[8]["environment"]["rounding"], "nearest_even")
            self.assertEqual(rows[7]["operands"], rows[8]["operands"])

    def test_nondefault_rounding_requires_nearest_even_baseline(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.set1.f64x2.default").data)
        data["environment"]["fp_rounding_modes"] = ["toward_zero"]
        data["regressions"] = {
            "rounding-toward-zero.v1": {
                "expected_intel": {
                    "observed": {
                        "return": {
                            "element": "f64",
                            "lanes": [
                                "0x0000000000000000",
                                "0x0000000000000000",
                            ],
                        }
                    },
                    "status": "ok",
                },
                "input_id": "0" * 64,
            }
        }
        with self.assertRaisesRegex(ValidationError, "nearest_even"):
            validate_case_definition(data, isa_registry=self.isa)

    def test_generator_rejects_a_registered_witness_it_cannot_materialize(self) -> None:
        data = copy.deepcopy(self.cases.get("sse2.set1.f64x2.default").data)
        data["regressions"] = {
            "missing-witness.v1": {
                "expected_intel": {
                    "observed": {
                        "return": {
                            "element": "f64",
                            "lanes": [
                                "0x0000000000000000",
                                "0x0000000000000000",
                            ],
                        }
                    },
                    "status": "ok",
                },
                "input_id": "f" * 64,
            }
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            case_path = root / "case.json"
            atomic_write(case_path, dump_bytes(data, newline=True))
            source = self.cases.get(data["id"]).source_path
            assert source is not None
            shutil.copyfile(source.parent / "development.py", root / "development.py")
            registry = load_case_definitions(case_path, isa_registry=self.isa)
            with self.assertRaisesRegex(ValidationError, "mandatory regressions"):
                generate_artifact(
                    cases=registry,
                    isa_registry=self.isa,
                    output=root / "vectors",
                    profile="smoke",
                    count_per_case=1,
                )
            self.assertFalse((root / "vectors/test-vectors.manifest.json").exists())

    def test_standard_profile_refuses_count_too_small_for_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValidationError, "at least 20"):
                generate_artifact(
                    cases=self.cases,
                    isa_registry=self.isa,
                    output=Path(temporary) / "vectors",
                    profile="standard",
                    count_per_case=19,
                )

    def test_standard_prefix_contains_registered_mandatory_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            generated = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=Path(temporary) / "vectors",
                profile="standard",
                count_per_case=20,
            )
            rows = list(iter_canonical_jsonl(generated.vectors_path))
            by_case: dict[str, list[dict[str, object]]] = {}
            for row in rows:
                by_case.setdefault(str(row["case_id"]), []).append(row)

            add_rows = by_case["sse2.add.f64x2.default"]
            self.assertTrue(any(row["generation"] == {"class": "boundary"} for row in add_rows))
            add_operand_pairs = [row["operands"] for row in add_rows]
            self.assertTrue(
                any(
                    operands["a"]["lanes"] == ["0x7fefffffffffffff"] * 2
                    and operands["b"]["lanes"] == ["0x7fefffffffffffff"] * 2
                    for operands in add_operand_pairs
                )
            )
            add_input_bits = {
                bits
                for operands in add_operand_pairs
                for argument in ("a", "b")
                for bits in operands[argument]["lanes"]
            }
            self.assertTrue(
                {
                    "0x8000000000000001",
                    "0x800fffffffffffff",
                    "0x8010000000000000",
                    "0xffefffffffffffff",
                }.issubset(add_input_bits)
            )
            self.assertTrue(
                any(
                    operands["a"]["lanes"] == ["0x3ff0000000000000"] * 2
                    and operands["b"]["lanes"] == ["0x3ca8000000000000"] * 2
                    for operands in add_operand_pairs
                )
            )

            set1_bits = {
                row["operands"]["value"]["bits"]
                for row in by_case["sse2.set1.f64x2.default"]
            }
            self.assertTrue(
                {
                    "0x8000000000000001",
                    "0x800fffffffffffff",
                    "0x8010000000000000",
                    "0xffefffffffffffff",
                }.issubset(set1_bits)
            )
            immediates = {
                row["immediates"]["imm8"]
                for row in by_case["sse2.shuffle.i32x4.imm8"]
            }
            self.assertEqual(immediates, {0, 1, 27, 255})

    def test_random_record_seed_is_the_actual_splitmix_initial_state(self) -> None:
        seed = "0x0123456789abcdef"
        with tempfile.TemporaryDirectory() as temporary:
            generated = generate_artifact(
                cases=self.cases,
                isa_registry=self.isa,
                output=Path(temporary) / "vectors",
                profile="smoke",
                count_per_case=21,
                seed=seed,
            )
            rows = list(iter_canonical_jsonl(generated.vectors_path))
            set1_random = next(
                row
                for row in rows
                if row["case_id"] == "sse2.set1.f64x2.default"
                and row["generation"]["class"] == "random"
            )
            self.assertEqual(set1_random["generation"]["seed"], seed)
            generator = SplitMix64(int(seed, 16))
            generator.next()  # rounding-mode selection
            expected_bits = f"0x{generator.next():016x}"
            self.assertEqual(set1_random["operands"]["value"]["bits"], expected_bits)


if __name__ == "__main__":
    unittest.main()
