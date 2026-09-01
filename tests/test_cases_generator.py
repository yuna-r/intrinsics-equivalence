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
from ioitf.development import load_development_case, scalar, vector  # noqa: E402
from ioitf.errors import ValidationError  # noqa: E402
from ioitf.generator import SplitMix64, generate_artifact  # noqa: E402
from ioitf.isa import load_isa_registry, project_used_isa  # noqa: E402
from ioitf.records import derive_input_id  # noqa: E402


class CaseAndGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
        cls.cases = load_case_definitions(
            PROJECT / "10_official_suite" / "cases", isa_registry=cls.isa
        )

    def test_registry_and_used_projection(self) -> None:
        self.assertEqual(
            self.cases.ids,
            (
                "sse2.add.f64x2.default",
                "sse2.add.i16x8.default",
                "sse2.add.i32x4.default",
                "sse2.add.i64x2.default",
                "sse2.add.i8x16.default",
                "sse2.adds.i16x8.default",
                "sse2.adds.i8x16.default",
                "sse2.adds.u16x8.default",
                "sse2.adds.u8x16.default",
                "sse2.and.f64x2.default",
                "sse2.and.i32x4.default",
                "sse2.andnot.f64x2.default",
                "sse2.andnot.i32x4.default",
                "sse2.avg.u16x8.default",
                "sse2.avg.u8x16.default",
                "sse2.cast.f32x4.f64x2",
                "sse2.cast.f32x4.i32x4",
                "sse2.cast.f64x2.f32x4",
                "sse2.cast.f64x2.i64x2",
                "sse2.cast.i32x4.f32x4",
                "sse2.cast.i64x2.f64x2",
                "sse2.cmpeq.f64x2.default",
                "sse2.cmpeq.i16x8.default",
                "sse2.cmpeq.i32x4.default",
                "sse2.cmpeq.i8x16.default",
                "sse2.cmpge.f64x2.default",
                "sse2.cmpgt.f64x2.default",
                "sse2.cmpgt.i16x8.default",
                "sse2.cmpgt.i32x4.default",
                "sse2.cmpgt.i8x16.default",
                "sse2.cmple.f64x2.default",
                "sse2.cmplt.f64x2.default",
                "sse2.cmplt.i16x8.default",
                "sse2.cmplt.i32x4.default",
                "sse2.cmplt.i8x16.default",
                "sse2.cmpneq.f64x2.default",
                "sse2.cmpnge.f64x2.default",
                "sse2.cmpngt.f64x2.default",
                "sse2.cmpnle.f64x2.default",
                "sse2.cmpnlt.f64x2.default",
                "sse2.cmpord.f64x2.default",
                "sse2.cmpunord.f64x2.default",
                "sse2.comieq.f64x2.scalar",
                "sse2.comige.f64x2.scalar",
                "sse2.comigt.f64x2.scalar",
                "sse2.comile.f64x2.scalar",
                "sse2.comilt.f64x2.scalar",
                "sse2.comineq.f64x2.scalar",
                "sse2.cvtsi128.i32x4.low",
                "sse2.cvtsi128.i64x2.low",
                "sse2.cvtsi32.i32x4.default",
                "sse2.cvtsi64.i64x2.default",
                "sse2.extract.i16x8.imm8",
                "sse2.insert.i16x8.imm8",
                "sse2.madd.i16x8.default",
                "sse2.max.f64x2.default",
                "sse2.max.i16x8.default",
                "sse2.max.u8x16.default",
                "sse2.min.f64x2.default",
                "sse2.min.i16x8.default",
                "sse2.min.u8x16.default",
                "sse2.move.f64x2.default",
                "sse2.move.i64x2.default",
                "sse2.movemask.f64x2.default",
                "sse2.movemask.i8x16.default",
                "sse2.mul.f64x2.default",
                "sse2.mul.u32x4.default",
                "sse2.mulhi.i16x8.default",
                "sse2.mulhi.u16x8.default",
                "sse2.mullo.i16x8.default",
                "sse2.or.f64x2.default",
                "sse2.or.i32x4.default",
                "sse2.packs.i16x8.default",
                "sse2.packs.i32x4.default",
                "sse2.packus.i16x8.default",
                "sse2.sad.u8x16.default",
                "sse2.set.f64x2.high-low",
                "sse2.set.i16x8.high-low",
                "sse2.set.i32x4.high-low",
                "sse2.set.i64x2.high-low",
                "sse2.set.i8x16.high-low",
                "sse2.set1.f64x2.default",
                "sse2.set1.i32x4.default",
                "sse2.set1.i64x2.default",
                "sse2.setr.i32x4.low-high",
                "sse2.shuffle.f64x2.imm8",
                "sse2.shuffle.i32x4.imm8",
                "sse2.shufflehi.i16x8.imm8",
                "sse2.shufflelo.i16x8.imm8",
                "sse2.sll.i16x8.vector-count",
                "sse2.sll.i32x4.vector-count",
                "sse2.sll.i64x2.vector-count",
                "sse2.slli-bytes.u8x16.imm8",
                "sse2.slli.i16x8.imm8",
                "sse2.slli.i32x4.imm8",
                "sse2.slli.i64x2.imm8",
                "sse2.sra.i16x8.vector-count",
                "sse2.sra.i32x4.vector-count",
                "sse2.srai.i16x8.imm8",
                "sse2.srai.i32x4.imm8",
                "sse2.srl.i16x8.vector-count",
                "sse2.srl.i32x4.vector-count",
                "sse2.srl.i64x2.vector-count",
                "sse2.srli-bytes.u8x16.imm8",
                "sse2.srli.i16x8.imm8",
                "sse2.srli.i32x4.imm8",
                "sse2.srli.i64x2.imm8",
                "sse2.sub.f64x2.default",
                "sse2.sub.i16x8.default",
                "sse2.sub.i32x4.default",
                "sse2.sub.i64x2.default",
                "sse2.sub.i8x16.default",
                "sse2.subs.i16x8.default",
                "sse2.subs.i8x16.default",
                "sse2.subs.u16x8.default",
                "sse2.subs.u8x16.default",
                "sse2.unpackhi.f64x2.default",
                "sse2.unpackhi.i16x8.default",
                "sse2.unpackhi.i32x4.default",
                "sse2.unpackhi.i64x2.default",
                "sse2.unpackhi.i8x16.default",
                "sse2.unpacklo.f64x2.default",
                "sse2.unpacklo.i16x8.default",
                "sse2.unpacklo.i32x4.default",
                "sse2.unpacklo.i64x2.default",
                "sse2.unpacklo.i8x16.default",
                "sse2.xor.f64x2.default",
                "sse2.xor.i32x4.default",
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

    def test_vector_helper_formats_every_supported_lane_width(self) -> None:
        expected = {
            "f32": "0xffffffff",
            "f64": "0xffffffffffffffff",
            "i8": "0xff",
            "i16": "0xffff",
            "i32": "0xffffffff",
            "i64": "0xffffffffffffffff",
            "u8": "0xff",
            "u16": "0xffff",
            "u32": "0xffffffff",
            "u64": "0xffffffffffffffff",
        }
        for element, lane in expected.items():
            with self.subTest(element=element):
                self.assertEqual(vector(element, (-1,))["lanes"], [lane])

    def test_scalar_helper_formats_every_supported_width(self) -> None:
        expected = {
            "f32": "0xffffffff",
            "f64": "0xffffffffffffffff",
            "i8": "0xff",
            "i16": "0xffff",
            "i32": "0xffffffff",
            "i64": "0xffffffffffffffff",
            "u8": "0xff",
            "u16": "0xffff",
            "u32": "0xffffffff",
            "u64": "0xffffffffffffffff",
        }
        for element, bits in expected.items():
            with self.subTest(element=element):
                self.assertEqual(scalar(element, -1), {"bits": bits, "element": element})

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
            self.assertEqual(first.record_count, 640)
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

    def test_added_case_models_have_known_results(self) -> None:
        records = {
            "sse2.sub.f64x2.default": {
                "operands": {
                    "a": {
                        "element": "f64",
                        "lanes": ["0x4024000000000000", "0xc010000000000000"],
                    },
                    "b": {
                        "element": "f64",
                        "lanes": ["0x4008000000000000", "0x4000000000000000"],
                    },
                }
            },
            "sse2.mul.f64x2.default": {
                "operands": {
                    "a": {
                        "element": "f64",
                        "lanes": ["0x4000000000000000", "0xc008000000000000"],
                    },
                    "b": {
                        "element": "f64",
                        "lanes": ["0x4010000000000000", "0x3fe0000000000000"],
                    },
                }
            },
            "sse2.and.i32x4.default": {
                "operands": {
                    "a": {
                        "element": "i32",
                        "lanes": [
                            "0xffffffff",
                            "0x0f0f0f0f",
                            "0xaaaaaaaa",
                            "0x80000000",
                        ],
                    },
                    "b": {
                        "element": "i32",
                        "lanes": [
                            "0x12345678",
                            "0xf0f0f0f0",
                            "0x55555555",
                            "0xffffffff",
                        ],
                    },
                }
            },
        }
        expected = {
            "sse2.sub.f64x2.default": {
                "return": {
                    "element": "f64",
                    "lanes": ["0x401c000000000000", "0xc018000000000000"],
                }
            },
            "sse2.mul.f64x2.default": {
                "return": {
                    "element": "f64",
                    "lanes": ["0x4020000000000000", "0xbff8000000000000"],
                }
            },
            "sse2.and.i32x4.default": {
                "return": {
                    "element": "i32",
                    "lanes": [
                        "0x12345678",
                        "0x00000000",
                        "0x00000000",
                        "0x80000000",
                    ],
                }
            },
        }

        for case_id, record in records.items():
            with self.subTest(case_id=case_id):
                case = self.cases.get(case_id)
                actual = load_development_case(case).execute(record)
                self.assertEqual(actual, expected[case_id])

    def test_extended_integer_models_have_known_results(self) -> None:
        arithmetic_record = {
            "operands": {
                "a": {
                    "element": "i32",
                    "lanes": [
                        "0xffffffff",
                        "0x7fffffff",
                        "0x80000000",
                        "0x12345678",
                    ],
                },
                "b": {
                    "element": "i32",
                    "lanes": [
                        "0x00000001",
                        "0x00000002",
                        "0xffffffff",
                        "0xfedcba98",
                    ],
                },
            }
        }
        arithmetic_expected = {
            "sse2.add.i32x4.default": [
                "0x00000000",
                "0x80000001",
                "0x7fffffff",
                "0x11111110",
            ],
            "sse2.sub.i32x4.default": [
                "0xfffffffe",
                "0x7ffffffd",
                "0x80000001",
                "0x13579be0",
            ],
            "sse2.or.i32x4.default": [
                "0xffffffff",
                "0x7fffffff",
                "0xffffffff",
                "0xfefcfef8",
            ],
            "sse2.xor.i32x4.default": [
                "0xfffffffe",
                "0x7ffffffd",
                "0x7fffffff",
                "0xece8ece0",
            ],
            "sse2.andnot.i32x4.default": [
                "0x00000000",
                "0x00000000",
                "0x7fffffff",
                "0xecc8a880",
            ],
        }
        for case_id, lanes in arithmetic_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    arithmetic_record
                )
                self.assertEqual(actual, {"return": {"element": "i32", "lanes": lanes}})

        comparison_record = {
            "operands": {
                "a": {
                    "element": "i32",
                    "lanes": [
                        "0x00000000",
                        "0xffffffff",
                        "0x7fffffff",
                        "0x80000000",
                    ],
                },
                "b": {
                    "element": "i32",
                    "lanes": [
                        "0xffffffff",
                        "0xfffffffe",
                        "0x00000000",
                        "0x80000000",
                    ],
                },
            }
        }
        comparison_expected = {
            "sse2.cmpeq.i32x4.default": [
                "0x00000000",
                "0x00000000",
                "0x00000000",
                "0xffffffff",
            ],
            "sse2.cmpgt.i32x4.default": [
                "0xffffffff",
                "0xffffffff",
                "0xffffffff",
                "0x00000000",
            ],
        }
        for case_id, lanes in comparison_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    comparison_record
                )
                self.assertEqual(actual, {"return": {"element": "i32", "lanes": lanes}})

        shift_operands = {
            "a": {
                "element": "i32",
                "lanes": [
                    "0x00000001",
                    "0x80000000",
                    "0xffffffff",
                    "0x12345678",
                ],
            }
        }
        shift_expected = {
            "sse2.slli.i32x4.imm8": [
                "0x00000002",
                "0x00000000",
                "0xfffffffe",
                "0x2468acf0",
            ],
            "sse2.srli.i32x4.imm8": [
                "0x00000000",
                "0x40000000",
                "0x7fffffff",
                "0x091a2b3c",
            ],
            "sse2.srai.i32x4.imm8": [
                "0x00000000",
                "0xc0000000",
                "0xffffffff",
                "0x091a2b3c",
            ],
        }
        for case_id, lanes in shift_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    {"immediates": {"imm8": 1}, "operands": shift_operands}
                )
                self.assertEqual(actual, {"return": {"element": "i32", "lanes": lanes}})

        wide_shift_expected = {
            "sse2.slli.i32x4.imm8": ["0x00000000"] * 4,
            "sse2.srli.i32x4.imm8": ["0x00000000"] * 4,
            "sse2.srai.i32x4.imm8": [
                "0x00000000",
                "0xffffffff",
                "0xffffffff",
                "0x00000000",
            ],
        }
        for case_id, lanes in wide_shift_expected.items():
            with self.subTest(case_id=case_id, imm8=32):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    {"immediates": {"imm8": 32}, "operands": shift_operands}
                )
                self.assertEqual(actual, {"return": {"element": "i32", "lanes": lanes}})

        unpack_record = {
            "operands": {
                "a": {
                    "element": "i32",
                    "lanes": [
                        "0x00000001",
                        "0x00000002",
                        "0x00000003",
                        "0x00000004",
                    ],
                },
                "b": {
                    "element": "i32",
                    "lanes": [
                        "0x0000000a",
                        "0x0000000b",
                        "0x0000000c",
                        "0x0000000d",
                    ],
                },
            }
        }
        unpack_expected = {
            "sse2.unpacklo.i32x4.default": [
                "0x00000001",
                "0x0000000a",
                "0x00000002",
                "0x0000000b",
            ],
            "sse2.unpackhi.i32x4.default": [
                "0x00000003",
                "0x0000000c",
                "0x00000004",
                "0x0000000d",
            ],
        }
        for case_id, lanes in unpack_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    unpack_record
                )
                self.assertEqual(actual, {"return": {"element": "i32", "lanes": lanes}})

    def test_extended_f64_bit_models_have_known_results(self) -> None:
        record = {
            "operands": {
                "a": {
                    "element": "f64",
                    "lanes": ["0xffff0000ffff0000", "0x0123456789abcdef"],
                },
                "b": {
                    "element": "f64",
                    "lanes": ["0x0f0f0f0f0f0f0f0f", "0xfedcba9876543210"],
                },
            }
        }
        expected = {
            "sse2.and.f64x2.default": [
                "0x0f0f00000f0f0000",
                "0x0000000000000000",
            ],
            "sse2.or.f64x2.default": [
                "0xffff0f0fffff0f0f",
                "0xffffffffffffffff",
            ],
            "sse2.xor.f64x2.default": [
                "0xf0f00f0ff0f00f0f",
                "0xffffffffffffffff",
            ],
            "sse2.unpacklo.f64x2.default": [
                "0xffff0000ffff0000",
                "0x0f0f0f0f0f0f0f0f",
            ],
            "sse2.unpackhi.f64x2.default": [
                "0x0123456789abcdef",
                "0xfedcba9876543210",
            ],
            "sse2.move.f64x2.default": [
                "0x0f0f0f0f0f0f0f0f",
                "0x0123456789abcdef",
            ],
        }
        for case_id, lanes in expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": {"element": "f64", "lanes": lanes}})

    def test_128_case_expansion_has_independent_known_results(self) -> None:
        def execute(
            case_id: str,
            operands: dict[str, object],
            immediates: dict[str, object] | None = None,
        ) -> dict[str, object]:
            record: dict[str, object] = {"operands": operands}
            if immediates is not None:
                record["immediates"] = immediates
            return load_development_case(self.cases.get(case_id)).execute(record)  # type: ignore[arg-type,return-value]

        shift_specs = (
            ("i16", 8, "0001", "8000", "0002", "0000", "4000", "c000"),
            ("i32", 4, "00000001", "80000000", "00000002", "00000000", "40000000", "c0000000"),
            ("i64", 2, "0000000000000001", "8000000000000000", "0000000000000002", "0000000000000000", "4000000000000000", None),
        )
        for element, lanes, one, sign, left_one, left_sign, right_sign, arithmetic_sign in shift_specs:
            source = [f"0x{one}", f"0x{sign}"] + [f"0x{one}"] * (lanes - 2)
            operands = {
                "a": {"element": element, "lanes": source},
                "count": {
                    "element": "u64",
                    "lanes": ["0x0000000000000001", "0xffffffffffffffff"],
                },
            }
            expected = {
                "sll": [f"0x{left_one}", f"0x{left_sign}"] + [f"0x{left_one}"] * (lanes - 2),
                "srl": [f"0x{'0' * len(one)}", f"0x{right_sign}"] + [f"0x{'0' * len(one)}"] * (lanes - 2),
            }
            if arithmetic_sign is not None:
                expected["sra"] = [f"0x{'0' * len(one)}", f"0x{arithmetic_sign}"] + [f"0x{'0' * len(one)}"] * (lanes - 2)
            for operation, output in expected.items():
                with self.subTest(case=f"{operation}-{element}"):
                    self.assertEqual(
                        execute(f"sse2.{operation}.{element}x{lanes}.vector-count", operands),
                        {"return": {"element": element, "lanes": output}},
                    )

        for element, lanes, width in (("i8", 16, 8), ("i16", 8, 16), ("i32", 4, 32)):
            mask = (1 << width) - 1
            sign = 1 << (width - 1)
            a_values = tuple((0, mask, sign - 1, sign) * (lanes // 4))
            b_values = tuple((mask, 0, 0, sign) * (lanes // 4))
            expected = tuple((0, mask, 0, 0) * (lanes // 4))
            self.assertEqual(
                execute(
                    f"sse2.cmplt.{element}x{lanes}.default",
                    {"a": vector(element, a_values), "b": vector(element, b_values)},
                ),
                {"return": vector(element, expected)},
            )

        self.assertEqual(
            execute(
                "sse2.cvtsi128.i32x4.low",
                {"a": vector("i32", (0x89ABCDEF, 1, 2, 3))},
            ),
            {"return": scalar("i32", 0x89ABCDEF)},
        )
        self.assertEqual(
            execute(
                "sse2.cvtsi128.i64x2.low",
                {"a": vector("i64", (0x0123456789ABCDEF, 0xFEDCBA9876543210))},
            ),
            {"return": scalar("i64", 0x0123456789ABCDEF)},
        )

        for element, lanes in (("i8", 16), ("i16", 8), ("i32", 4), ("i64", 2)):
            arguments = {
                f"lane{lane}": scalar(element, lane + 1) for lane in reversed(range(lanes))
            }
            self.assertEqual(
                execute(f"sse2.set.{element}x{lanes}.high-low", arguments),
                {"return": vector(element, tuple(range(1, lanes + 1)))},
            )
        setr_operands = {f"lane{lane}": scalar("i32", lane + 10) for lane in range(4)}
        self.assertEqual(
            execute("sse2.setr.i32x4.low-high", setr_operands),
            {"return": vector("i32", (10, 11, 12, 13))},
        )

        i16_source = vector("i16", (0x1000, 0x2111, 0x3222, 0x4333, 0x5444, 0x6555, 0x7666, 0x8777))
        self.assertEqual(
            execute("sse2.extract.i16x8.imm8", {"a": i16_source}, {"imm8": 5}),
            {"return": scalar("u32", 0x6555)},
        )
        self.assertEqual(
            execute(
                "sse2.insert.i16x8.imm8",
                {"a": i16_source, "value": scalar("i32", 0xDEADBEEF)},
                {"imm8": 2},
            ),
            {"return": vector("i16", (0x1000, 0x2111, 0xBEEF, 0x4333, 0x5444, 0x6555, 0x7666, 0x8777))},
        )

        f64_bits = vector("f64", (0x0123456789ABCDEF, 0xFEDCBA9876543210))
        f32_bits = vector("f32", (0x89ABCDEF, 0x01234567, 0x76543210, 0xFEDCBA98))
        self.assertEqual(
            execute("sse2.cast.f64x2.f32x4", {"a": f64_bits}),
            {"return": f32_bits},
        )
        self.assertEqual(
            execute("sse2.cast.f32x4.f64x2", {"a": f32_bits}),
            {"return": f64_bits},
        )
        self.assertEqual(
            execute("sse2.cast.f32x4.i32x4", {"a": f32_bits}),
            {"return": vector("i32", (0x89ABCDEF, 0x01234567, 0x76543210, 0xFEDCBA98))},
        )
        self.assertEqual(
            execute(
                "sse2.cast.i32x4.f32x4",
                {"a": vector("i32", (0x89ABCDEF, 0x01234567, 0x76543210, 0xFEDCBA98))},
            ),
            {"return": f32_bits},
        )

        float_operands = {
            "a": vector("f64", (0x3FF0000000000000, 0x7FF8000000000042)),
            "b": vector("f64", (0x4000000000000000, 0xBFF0000000000000)),
        }
        self.assertEqual(
            execute("sse2.min.f64x2.default", float_operands),
            {"return": vector("f64", (0x3FF0000000000000, 0xBFF0000000000000))},
        )
        self.assertEqual(
            execute("sse2.max.f64x2.default", float_operands),
            {"return": vector("f64", (0x4000000000000000, 0xBFF0000000000000))},
        )

        unordered = {
            "a": vector("f64", (0x7FF8000000000042, 0)),
            "b": vector("f64", (0x3FF0000000000000, 0)),
        }
        for operation, expected in {
            "comieq": 0,
            "comilt": 0,
            "comile": 0,
            "comigt": 0,
            "comige": 0,
            "comineq": 1,
        }.items():
            with self.subTest(case=operation, unordered=True):
                self.assertEqual(
                    execute(f"sse2.{operation}.f64x2.scalar", unordered),
                    {"return": scalar("i32", expected)},
                )

    def test_f64_comparison_models_cover_ordered_unordered_and_signed_zero(self) -> None:
        true = "0xffffffffffffffff"
        false = "0x0000000000000000"
        scenarios = (
            (
                ["0x0000000000000000", "0x4000000000000000"],
                ["0x8000000000000000", "0x3ff0000000000000"],
                {
                    "cmpeq": [true, false],
                    "cmplt": [false, false],
                    "cmple": [true, false],
                    "cmpgt": [false, true],
                    "cmpge": [true, true],
                    "cmpneq": [false, true],
                    "cmpord": [true, true],
                    "cmpunord": [false, false],
                },
            ),
            (
                ["0x7ff8000000000042", "0x3ff0000000000000"],
                ["0x3ff0000000000000", "0x7ff0000000000001"],
                {
                    "cmpeq": [false, false],
                    "cmplt": [false, false],
                    "cmple": [false, false],
                    "cmpgt": [false, false],
                    "cmpge": [false, false],
                    "cmpneq": [true, true],
                    "cmpord": [false, false],
                    "cmpunord": [true, true],
                },
            ),
        )
        for left, right, expected in scenarios:
            record = {
                "operands": {
                    "a": {"element": "f64", "lanes": left},
                    "b": {"element": "f64", "lanes": right},
                }
            }
            for operation, lanes in expected.items():
                case_id = f"sse2.{operation}.f64x2.default"
                with self.subTest(case_id=case_id, left=left):
                    actual = load_development_case(self.cases.get(case_id)).execute(record)
                    self.assertEqual(
                        actual, {"return": {"element": "f64", "lanes": lanes}}
                    )

    def test_i8_and_i16_models_cover_wrap_saturation_and_signed_compare(self) -> None:
        specifications = (
            {
                "bits": 8,
                "element": "i8",
                "a": ["7f", "80", "ff", "00", "40", "c0", "7f", "80"] * 2,
                "b": ["01", "ff", "01", "ff", "40", "c0", "80", "7f"] * 2,
                "expected": {
                    "add.i8x16": ("i8", ["80", "7f", "00", "ff", "80", "80", "ff", "ff"] * 2),
                    "sub.i8x16": ("i8", ["7e", "81", "fe", "01", "00", "00", "ff", "01"] * 2),
                    "adds.i8x16": ("i8", ["7f", "80", "00", "ff", "7f", "80", "ff", "ff"] * 2),
                    "adds.u8x16": ("u8", ["80", "ff", "ff", "ff", "80", "ff", "ff", "ff"] * 2),
                    "subs.i8x16": ("i8", ["7e", "81", "fe", "01", "00", "00", "7f", "80"] * 2),
                    "subs.u8x16": ("u8", ["7e", "00", "fe", "00", "00", "00", "00", "01"] * 2),
                    "cmpeq.i8x16": ("i8", ["00", "00", "00", "00", "ff", "ff", "00", "00"] * 2),
                    "cmpgt.i8x16": ("i8", ["ff", "00", "00", "ff", "00", "00", "ff", "00"] * 2),
                },
            },
            {
                "bits": 16,
                "element": "i16",
                "a": ["7fff", "8000", "ffff", "0000", "4000", "c000", "7fff", "8000"],
                "b": ["0001", "ffff", "0001", "ffff", "4000", "c000", "8000", "7fff"],
                "expected": {
                    "add.i16x8": ("i16", ["8000", "7fff", "0000", "ffff", "8000", "8000", "ffff", "ffff"]),
                    "sub.i16x8": ("i16", ["7ffe", "8001", "fffe", "0001", "0000", "0000", "ffff", "0001"]),
                    "adds.i16x8": ("i16", ["7fff", "8000", "0000", "ffff", "7fff", "8000", "ffff", "ffff"]),
                    "adds.u16x8": ("u16", ["8000", "ffff", "ffff", "ffff", "8000", "ffff", "ffff", "ffff"]),
                    "subs.i16x8": ("i16", ["7ffe", "8001", "fffe", "0001", "0000", "0000", "7fff", "8000"]),
                    "subs.u16x8": ("u16", ["7ffe", "0000", "fffe", "0000", "0000", "0000", "0000", "0001"]),
                    "cmpeq.i16x8": ("i16", ["0000", "0000", "0000", "0000", "ffff", "ffff", "0000", "0000"]),
                    "cmpgt.i16x8": ("i16", ["ffff", "0000", "0000", "ffff", "0000", "0000", "ffff", "0000"]),
                },
            },
        )
        for specification in specifications:
            width = specification["bits"] // 4
            for suffix, (element, expected_lanes) in specification["expected"].items():
                case_id = f"sse2.{suffix}.default"
                operand_element = (
                    element if element.startswith("u") else specification["element"]
                )
                record = {
                    "operands": {
                        "a": {
                            "element": operand_element,
                            "lanes": [
                                f"0x{value}" for value in specification["a"]
                            ],
                        },
                        "b": {
                            "element": operand_element,
                            "lanes": [
                                f"0x{value}" for value in specification["b"]
                            ],
                        },
                    }
                }
                expected = {
                    "return": {
                        "element": element,
                        "lanes": [
                            f"0x{int(value, 16):0{width}x}" for value in expected_lanes
                        ],
                    }
                }
                with self.subTest(case_id=case_id):
                    actual = load_development_case(self.cases.get(case_id)).execute(record)
                    self.assertEqual(actual, expected)

    def test_new_multiply_models_have_independent_golden_results(self) -> None:
        a = (0x7FFF, 0x8000, 0xFFFF, 0x1234, 0xFFFE, 0x4000, 0xC000, 3)
        b = (2, 2, 0xFFFF, 0x10, 0x8000, 4, 0xFFFC, 5)
        specifications = {
            "sse2.mullo.i16x8.default": (
                "i16",
                (0xFFFE, 0, 1, 0x2340, 0, 0, 0, 0x000F),
            ),
            "sse2.mulhi.i16x8.default": (
                "i16",
                (0, 0xFFFF, 0, 1, 1, 1, 1, 0),
            ),
            "sse2.mulhi.u16x8.default": (
                "u16",
                (0, 1, 0xFFFE, 1, 0x7FFF, 1, 0xBFFD, 0),
            ),
            "sse2.madd.i16x8.default": (
                "i32",
                (0xFFFFFFFE, 0x00012341, 0x00020000, 0x0001000F),
            ),
        }
        for case_id, (result_element, expected) in specifications.items():
            operand_element = "u16" if ".u16x8." in case_id else "i16"
            record = {
                "operands": {
                    "a": vector(operand_element, a),
                    "b": vector(operand_element, b),
                }
            }
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": vector(result_element, expected)})

        unsigned_record = {
            "operands": {
                "a": vector("u32", (0xFFFFFFFF, 0x11111111, 0x80000000, 7)),
                "b": vector("u32", (2, 0x22222222, 0xFFFFFFFF, 9)),
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.mul.u32x4.default")
        ).execute(unsigned_record)
        self.assertEqual(
            actual,
            {
                "return": vector(
                    "u64", (0x00000001FFFFFFFE, 0x7FFFFFFF80000000)
                )
            },
        )

        overflow_record = {
            "operands": {
                "a": vector("i16", (0x8000,) * 8),
                "b": vector("i16", (0x8000,) * 8),
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.madd.i16x8.default")
        ).execute(overflow_record)
        self.assertEqual(
            actual, {"return": vector("i32", (0x80000000,) * 4)}
        )

    def test_new_average_reduction_and_minmax_models_have_golden_results(self) -> None:
        ascending = tuple(range(16))
        descending = tuple(reversed(ascending))
        byte_record = {
            "operands": {
                "a": vector("u8", ascending),
                "b": vector("u8", descending),
            }
        }
        byte_expected = {
            "sse2.avg.u8x16.default": vector("u8", (8,) * 16),
            "sse2.sad.u8x16.default": vector("u64", (64, 64)),
            "sse2.min.u8x16.default": vector(
                "u8", (0, 1, 2, 3, 4, 5, 6, 7, 7, 6, 5, 4, 3, 2, 1, 0)
            ),
            "sse2.max.u8x16.default": vector(
                "u8", (15, 14, 13, 12, 11, 10, 9, 8, 8, 9, 10, 11, 12, 13, 14, 15)
            ),
        }
        for case_id, expected in byte_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    byte_record
                )
                self.assertEqual(actual, {"return": expected})

        avg_record = {
            "operands": {
                "a": vector(
                    "u16", (0, 1, 0xFFFF, 0xFFFE, 0x8000, 0x7FFF, 0x1234, 0xAAAA)
                ),
                "b": vector(
                    "u16", (0, 2, 0xFFFF, 1, 0x8001, 0x7FFF, 0xEDCB, 0x5555)
                ),
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.avg.u16x8.default")
        ).execute(avg_record)
        self.assertEqual(
            actual,
            {
                "return": vector(
                    "u16", (0, 2, 0xFFFF, 0x8000, 0x8001, 0x7FFF, 0x8000, 0x8000)
                )
            },
        )

        signed_record = {
            "operands": {
                "a": vector(
                    "i16", (0x7FFF, 0x8000, 0xFFFF, 0x1234, 0xFFFE, 0x4000, 0xC000, 3)
                ),
                "b": vector("i16", (2, 2, 0xFFFF, 0x10, 0x8000, 4, 0xFFFC, 5)),
            }
        }
        signed_expected = {
            "sse2.min.i16x8.default": (2, 0x8000, 0xFFFF, 0x10, 0x8000, 4, 0xC000, 3),
            "sse2.max.i16x8.default": (0x7FFF, 2, 0xFFFF, 0x1234, 0xFFFE, 0x4000, 0xFFFC, 5),
        }
        for case_id, expected in signed_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    signed_record
                )
                self.assertEqual(actual, {"return": vector("i16", expected)})

    def test_new_shift_models_have_independent_golden_results(self) -> None:
        lanes16 = (1, 0x8000, 0xFFFF, 0x1234, 0x7FFF, 0x4000, 0xC000, 3)
        expected16 = {
            "sse2.slli.i16x8.imm8": (2, 0, 0xFFFE, 0x2468, 0xFFFE, 0x8000, 0x8000, 6),
            "sse2.srli.i16x8.imm8": (0, 0x4000, 0x7FFF, 0x091A, 0x3FFF, 0x2000, 0x6000, 1),
            "sse2.srai.i16x8.imm8": (0, 0xC000, 0xFFFF, 0x091A, 0x3FFF, 0x2000, 0xE000, 1),
        }
        for case_id, expected in expected16.items():
            record = {
                "immediates": {"imm8": 1},
                "operands": {"a": vector("i16", lanes16)},
            }
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": vector("i16", expected)})

        lanes64 = (1, 0x8000000000000001)
        expected64 = {
            "sse2.slli.i64x2.imm8": (0x8000000000000000, 0x8000000000000000),
            "sse2.srli.i64x2.imm8": (0, 1),
        }
        for case_id, expected in expected64.items():
            record = {
                "immediates": {"imm8": 63},
                "operands": {"a": vector("i64", lanes64)},
            }
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": vector("i64", expected)})

        bytes_record = {
            "immediates": {"imm8": 3},
            "operands": {"a": vector("u8", tuple(range(16)))},
        }
        byte_expected = {
            "sse2.slli-bytes.u8x16.imm8": (0, 0, 0, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
            "sse2.srli-bytes.u8x16.imm8": (3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 0, 0, 0),
        }
        for case_id, expected in byte_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    bytes_record
                )
                self.assertEqual(actual, {"return": vector("u8", expected)})

        wide16_expected = {
            "sse2.slli.i16x8.imm8": (0,) * 8,
            "sse2.srli.i16x8.imm8": (0,) * 8,
            "sse2.srai.i16x8.imm8": (0, 0xFFFF, 0xFFFF, 0, 0, 0, 0xFFFF, 0),
        }
        for case_id, expected in wide16_expected.items():
            record = {
                "immediates": {"imm8": 16},
                "operands": {"a": vector("i16", lanes16)},
            }
            with self.subTest(case_id=case_id, imm8=16):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": vector("i16", expected)})

    def test_new_i64_arithmetic_move_and_unpack_models_have_golden_results(self) -> None:
        arithmetic_record = {
            "operands": {
                "a": vector("i64", (0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF)),
                "b": vector("i64", (1, 1)),
            }
        }
        arithmetic_expected = {
            "sse2.add.i64x2.default": (0, 0x8000000000000000),
            "sse2.sub.i64x2.default": (0xFFFFFFFFFFFFFFFE, 0x7FFFFFFFFFFFFFFE),
        }
        for case_id, expected in arithmetic_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    arithmetic_record
                )
                self.assertEqual(actual, {"return": vector("i64", expected)})

        move_record = {
            "operands": {
                "a": vector("i64", (0x1111111111111111, 0x2222222222222222))
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.move.i64x2.default")
        ).execute(move_record)
        self.assertEqual(
            actual, {"return": vector("i64", (0x1111111111111111, 0))}
        )

        unpack_specs = (
            (
                "i8",
                tuple(range(16)),
                tuple(range(0x80, 0x90)),
                {
                    "sse2.unpacklo.i8x16.default": tuple(
                        value for pair in zip(range(8), range(0x80, 0x88)) for value in pair
                    ),
                    "sse2.unpackhi.i8x16.default": tuple(
                        value for pair in zip(range(8, 16), range(0x88, 0x90)) for value in pair
                    ),
                },
            ),
            (
                "i16",
                tuple(range(8)),
                tuple(range(0x10, 0x18)),
                {
                    "sse2.unpacklo.i16x8.default": (0, 0x10, 1, 0x11, 2, 0x12, 3, 0x13),
                    "sse2.unpackhi.i16x8.default": (4, 0x14, 5, 0x15, 6, 0x16, 7, 0x17),
                },
            ),
            (
                "i64",
                (1, 2),
                (0xA, 0xB),
                {
                    "sse2.unpacklo.i64x2.default": (1, 0xA),
                    "sse2.unpackhi.i64x2.default": (2, 0xB),
                },
            ),
        )
        for element, a, b, expectations in unpack_specs:
            record = {"operands": {"a": vector(element, a), "b": vector(element, b)}}
            for case_id, expected in expectations.items():
                with self.subTest(case_id=case_id):
                    actual = load_development_case(self.cases.get(case_id)).execute(
                        record
                    )
                    self.assertEqual(actual, {"return": vector(element, expected)})

    def test_new_pack_shuffle_and_construct_models_have_golden_results(self) -> None:
        a16 = (0x8000, 0xFF80, 0xFF7F, 0, 0x7F, 0x80, 0x7FFF, 0xFFFF)
        b16 = (1, 0xFF, 0xFF00, 0x7F00, 0x8100, 0x80, 0xFF81, 0x7E)
        pack_record = {
            "operands": {"a": vector("i16", a16), "b": vector("i16", b16)}
        }
        pack_expected = {
            "sse2.packs.i16x8.default": (
                "i8",
                (0x80, 0x80, 0x80, 0, 0x7F, 0x7F, 0x7F, 0xFF,
                 1, 0x7F, 0x80, 0x7F, 0x80, 0x7F, 0x81, 0x7E),
            ),
            "sse2.packus.i16x8.default": (
                "u8",
                (0, 0, 0, 0, 0x7F, 0x80, 0xFF, 0,
                 1, 0xFF, 0, 0xFF, 0, 0x80, 0, 0x7E),
            ),
        }
        for case_id, (element, expected) in pack_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    pack_record
                )
                self.assertEqual(actual, {"return": vector(element, expected)})

        packs32_record = {
            "operands": {
                "a": vector("i32", (0x80000000, 0xFFFF8000, 0xFFFF7FFF, 0)),
                "b": vector("i32", (0x7FFF, 0x8000, 0x7FFFFFFF, 0xFFFFFFFF)),
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.packs.i32x4.default")
        ).execute(packs32_record)
        self.assertEqual(
            actual,
            {
                "return": vector(
                    "i16", (0x8000, 0x8000, 0x8000, 0, 0x7FFF, 0x7FFF, 0x7FFF, 0xFFFF)
                )
            },
        )

        shuffle_record = {
            "immediates": {"imm8": 27},
            "operands": {"a": vector("i16", tuple(range(8)))},
        }
        shuffle_expected = {
            "sse2.shufflelo.i16x8.imm8": (3, 2, 1, 0, 4, 5, 6, 7),
            "sse2.shufflehi.i16x8.imm8": (0, 1, 2, 3, 7, 6, 5, 4),
        }
        for case_id, expected in shuffle_expected.items():
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(
                    shuffle_record
                )
                self.assertEqual(actual, {"return": vector("i16", expected)})

        pd_record = {
            "immediates": {"imm8": 2},
            "operands": {
                "a": vector("f64", (0x1111111111111111, 0x2222222222222222)),
                "b": vector("f64", (0xAAAAAAAAAAAAAAAA, 0xBBBBBBBBBBBBBBBB)),
            },
        }
        actual = load_development_case(
            self.cases.get("sse2.shuffle.f64x2.imm8")
        ).execute(pd_record)
        self.assertEqual(
            actual,
            {"return": vector("f64", (0x1111111111111111, 0xBBBBBBBBBBBBBBBB))},
        )

        constructors = (
            (
                "sse2.cvtsi32.i32x4.default",
                {"operands": {"value": scalar("i32", 0x89ABCDEF)}},
                vector("i32", (0x89ABCDEF, 0, 0, 0)),
            ),
            (
                "sse2.cvtsi64.i64x2.default",
                {"operands": {"value": scalar("i64", 0xFEDCBA9876543210)}},
                vector("i64", (0xFEDCBA9876543210, 0)),
            ),
            (
                "sse2.set1.i32x4.default",
                {"operands": {"value": scalar("i32", 0x89ABCDEF)}},
                vector("i32", (0x89ABCDEF,) * 4),
            ),
            (
                "sse2.set1.i64x2.default",
                {"operands": {"value": scalar("i64", 0xFEDCBA9876543210)}},
                vector("i64", (0xFEDCBA9876543210,) * 2),
            ),
            (
                "sse2.set.f64x2.high-low",
                {
                    "operands": {
                        "high": scalar("f64", 0xAAAAAAAAAAAAAAAA),
                        "low": scalar("f64", 0x1111111111111111),
                    }
                },
                vector("f64", (0x1111111111111111, 0xAAAAAAAAAAAAAAAA)),
            ),
        )
        for case_id, record, expected in constructors:
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": expected})

    def test_new_bitcast_mask_and_negated_compare_models_have_golden_results(self) -> None:
        lanes = (0x0123456789ABCDEF, 0xFEDCBA9876543210)
        casts = (
            ("sse2.cast.i64x2.f64x2", "i64", "f64"),
            ("sse2.cast.f64x2.i64x2", "f64", "i64"),
        )
        for case_id, source, result in casts:
            record = {"operands": {"a": vector(source, lanes)}}
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": vector(result, lanes)})

        bit_record = {
            "operands": {
                "a": vector("f64", (0xFFFF0000FFFF0000, 0x0123456789ABCDEF)),
                "b": vector("f64", (0x0F0F0F0F0F0F0F0F, 0xFEDCBA9876543210)),
            }
        }
        actual = load_development_case(
            self.cases.get("sse2.andnot.f64x2.default")
        ).execute(bit_record)
        self.assertEqual(
            actual,
            {"return": vector("f64", (0x00000F0F00000F0F, 0xFEDCBA9876543210))},
        )

        masks = (
            (
                "sse2.movemask.i8x16.default",
                {"operands": {"a": vector("i8", (0x80, 0, 0, 0xFF, 0, 0, 0, 0, 0x80, 0, 0, 0, 0, 0, 0, 0x80))}},
                0x00008109,
            ),
            (
                "sse2.movemask.f64x2.default",
                {"operands": {"a": vector("f64", (0, 0x8000000000000000))}},
                2,
            ),
        )
        for case_id, record, expected in masks:
            with self.subTest(case_id=case_id):
                actual = load_development_case(self.cases.get(case_id)).execute(record)
                self.assertEqual(actual, {"return": scalar("i32", expected)})

        true = 0xFFFFFFFFFFFFFFFF
        false = 0
        ordered_record = {
            "operands": {
                "a": vector("f64", (0x3FF0000000000000, 0x4000000000000000)),
                "b": vector("f64", (0x3FF0000000000000, 0x3FF0000000000000)),
            }
        }
        expected = {
            "sse2.cmpnlt.f64x2.default": (true, true),
            "sse2.cmpnle.f64x2.default": (false, true),
            "sse2.cmpngt.f64x2.default": (true, false),
            "sse2.cmpnge.f64x2.default": (false, false),
        }
        for case_id, lanes_expected in expected.items():
            with self.subTest(case_id=case_id):
                pack = load_development_case(self.cases.get(case_id))
                self.assertEqual(
                    pack.execute(ordered_record),
                    {"return": vector("f64", lanes_expected)},
                )
                unordered = {
                    "operands": {
                        "a": vector("f64", (0x7FF8000000000042, 0x7FF0000000000001)),
                        "b": vector("f64", (0x3FF0000000000000, 0x4000000000000000)),
                    }
                }
                self.assertEqual(
                    pack.execute(unordered),
                    {"return": vector("f64", (true, true))},
                )

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
