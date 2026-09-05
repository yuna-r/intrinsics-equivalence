"""Independent bit-pattern oracles for bugs shared by both fixture roles.

These are ordinary failing assertions, deliberately not expectedFailure tests.
See tests/BUG_HUNT.md for reproduction and the independent SSE2 probe.
"""

from pathlib import Path
import copy
import hashlib
import json
import sys
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.cases import load_case_definitions, validate_case_definition
from ioitf.development import load_development_case, vector
from ioitf.isa import load_isa_registry
from ioitf.oracle import ModelOutputMismatch
from ioitf.records import derive_input_id, validate_input_record


# Literal SSE2 results; never compute an oracle with the model under test or
# with host floating-point arithmetic. Tuple fields: +inf, qNaN, sNaN,
# quieted sNaN, indefinite NaN, sign bit, one.
FLOAT_BITS = {
    "f32": (0x7F800000, 0x7FC00042, 0x7F800001, 0x7FC00001,
            0xFFC00000, 0x80000000, 0x3F800000),
    "f64": (0x7FF0000000000000, 0x7FF8000000000042,
            0x7FF0000000000001, 0x7FF8000000000001,
            0xFFF8000000000000, 0x8000000000000000,
            0x3FF0000000000000),
}


class AdversarialModelTests(unittest.TestCase):
    verification_subject = "portable_model_oracle"

    @classmethod
    def setUpClass(cls):
        cls.isa = load_isa_registry(PROJECT / "contracts" / "isa-registry.json")
        cls.cases = load_case_definitions(
            PROJECT / "10_official_suite" / "cases", isa_registry=cls.isa
        )
        cls.rounding_corpus = json.loads((PROJECT / "tests/data/rounding-oracles.json").read_text())
        cls.oracle_reference_metadata = {
            key: value for key, value in cls.rounding_corpus.items() if key != "rows"
        }
        cls.oracle_reference_metadata["row_count"] = len(cls.rounding_corpus["rows"])

    def test_captured_oracle_sources_have_not_changed(self):
        for relative, expected in self.rounding_corpus["source_sha256"].items():
            with self.subTest(source=relative):
                self.assertEqual(hashlib.sha256((PROJECT / relative).read_bytes()).hexdigest(), expected,
                                 "Rebuild the SSE2 probe and recapture/verify its oracle after source changes")

    def assert_model(self, case_id, operands, expected, *, rounding="nearest_even",
                     extended=False, family=None, buffers=None, observed=None):
        case = self.cases.get(case_id)
        record = {
            "schema_version": 1,
            "case_id": case_id,
            "sequence": 1,
            "generation": {"class": "structured"},
            "environment": {"fp_mode": "ieee", "rounding": rounding},
            "operands": operands,
        }
        if buffers is not None:
            record["buffers"] = buffers
        wanted = observed if observed is not None else {"return": expected}
        record["input_id"] = derive_input_id(record)
        if extended:
            # Official packs remain nearest-even only. Validate an explicit
            # extension with a captured Intel witness before evaluating it.
            data = copy.deepcopy(case.data)
            data["environment"]["fp_rounding_modes"] = sorted({"nearest_even", rounding})
            data["regressions"] = {"captured-rounding.v1": {
                "input_id": record["input_id"],
                "expected_intel": {"status": "ok", "observed": wanted},
            }}
            case = validate_case_definition(data, isa_registry=self.isa, source_path=case.source_path)
            record["generation"] = {"class": "regression", "regression_id": "captured-rounding.v1"}
        # Validate the official contract or the explicitly recorded extension.
        validate_input_record(record, case)
        actual = load_development_case(case).execute(record)
        self.oracle_checks = getattr(self, "oracle_checks", 0) + 1
        if actual != wanted:
            if family is None:
                family = ("nan_payload_priority" if "payload_priority" in self._testMethodName
                          else "nan_indefinite_sign" if "indefinite_nan" in self._testMethodName
                          else "output_mismatch")
            raise ModelOutputMismatch(
                input_record=record, expected=wanted, actual=actual,
                finding_family=family,
                contract_scope="validated_rounding_extension" if extended else "official_nearest_even",
                case_contract=case.data if extended else None,
                oracle_reference="tests/data/rounding-oracles.json" if extended else "tests/BUG_HUNT.md",
            )

    def check_rounding_family(self, family):
        rows = [row for row in self.rounding_corpus["rows"] if row["family"] == family]
        self.assertTrue(rows, "the independent oracle corpus must contain this family")
        for row in rows:
            with self.subTest(case_id=row["case_id"], rounding=row["rounding"], input=row["label"]):
                self.assert_model(row["case_id"], row["operands"], row["expected"]["return"],
                                  rounding=row["rounding"], extended=True, family=family)

    def test_requested_rounding_in_arithmetic(self):
        self.check_rounding_family("rounding_arithmetic")

    def test_requested_rounding_in_sqrt(self):
        self.check_rounding_family("rounding_sqrt")

    def test_requested_rounding_in_float_to_integer_and_truncation_control(self):
        self.check_rounding_family("rounding_float_to_integer")

    def test_requested_rounding_in_narrowing(self):
        self.check_rounding_family("rounding_narrowing")

    def test_requested_rounding_in_integer_to_float(self):
        self.check_rounding_family("rounding_integer_to_float")

    def assert_float_binary(self, operation, element, variant, a, b, expected):
        lanes = 4 if element == "f32" else 2
        _, qnan, snan, _, _, sign, _ = FLOAT_BITS[element]
        # Distinct poison lanes detect evaluating/copying the wrong operand
        # and quieting an inactive signaling NaN in scalar instructions.
        upper_a = (snan, sign, qnan)[:lanes - 1]
        upper_b = (qnan, 1, snan)[:lanes - 1]
        if variant == "scalar":
            left, right = (a,) + upper_a, (b,) + upper_b
            wanted = (expected,) + upper_a
        else:
            left, right, wanted = (a,) * lanes, (b,) * lanes, (expected,) * lanes
        self.assert_model(
            f"sse2.{operation}.{element}x{lanes}.{variant}",
            {"a": vector(element, left), "b": vector(element, right)},
            vector(element, wanted),
        )

    def check_invalid_arithmetic(self, operation):
        for element, (inf, _, _, _, indefinite, sign, _) in FLOAT_BITS.items():
            a, b = {"add": (inf, inf | sign),
                    "sub": (inf, inf), "mul": (0, inf)}[operation]
            for variant in ("default", "scalar"):
                with self.subTest(element=element, variant=variant):
                    self.assert_float_binary(operation, element, variant, a, b, indefinite)

    def test_add_opposite_infinities_returns_negative_indefinite_nan(self):
        self.check_invalid_arithmetic("add")

    def test_sub_equal_infinities_returns_negative_indefinite_nan(self):
        self.check_invalid_arithmetic("sub")

    def test_mul_zero_infinity_returns_negative_indefinite_nan(self):
        self.check_invalid_arithmetic("mul")

    def test_nan_payload_priority_is_first_operand_even_when_second_signals(self):
        for element, (_, qnan, snan, quiet_snan, _, sign, _) in FLOAT_BITS.items():
            for a, b, expected in (
                (qnan, snan, qnan),
                (snan, qnan, quiet_snan),
                (qnan | sign, snan, qnan | sign),
            ):
                for operation in ("add", "sub", "mul", "div"):
                    for variant in ("default", "scalar"):
                        with self.subTest(element=element, operation=operation,
                                          variant=variant, a=hex(a), b=hex(b)):
                            self.assert_float_binary(
                                operation, element, variant, a, b, expected
                            )

    def test_minmax_returns_second_operand_bits_for_nan_and_zero_ties(self):
        for element, (_, qnan, snan, _, _, sign, one) in FLOAT_BITS.items():
            for a, b in ((0, sign), (sign, 0), (qnan, one),
                         (one, snan), (qnan, snan)):
                for operation in ("min", "max"):
                    for variant in ("default", "scalar"):
                        with self.subTest(element=element, operation=operation,
                                          variant=variant, a=hex(a), b=hex(b)):
                            self.assert_float_binary(operation, element, variant, a, b, b)

    def test_arithmetic_signed_zero_and_scalar_inactive_lanes(self):
        for element, (_, _, _, _, _, sign, one) in FLOAT_BITS.items():
            for operation, a, b, expected in (
                ("add", sign, sign, sign), ("add", sign, 0, 0),
                ("sub", sign, 0, sign), ("sub", sign, sign, 0),
                ("mul", sign, one, sign), ("div", 0, one | sign, sign),
            ):
                for variant in ("default", "scalar"):
                    with self.subTest(element=element, operation=operation,
                                      variant=variant, a=hex(a), b=hex(b)):
                        self.assert_float_binary(operation, element, variant, a, b, expected)

    def test_narrowing_rounds_both_sides_of_halfway_and_zeros_unused_lanes(self):
        # Neighboring binary64 encodings around binary32 rounding midpoints.
        # Cover even/odd significands, underflow, the normal/subnormal boundary,
        # and overflow. Each row is (midpoint, below, tie, above).
        rows = (
            (0x3FF0000010000000, 0x3F800000, 0x3F800000, 0x3F800001),
            (0x3FF0000030000000, 0x3F800001, 0x3F800002, 0x3F800002),
            (0x3690000000000000, 0x00000000, 0x00000000, 0x00000001),
            (0x380FFFFFE0000000, 0x007FFFFF, 0x00800000, 0x00800000),
            (0x47EFFFFFF0000000, 0x7F7FFFFF, 0x7F800000, 0x7F800000),
        )
        for midpoint, below, tie, above in rows:
            for offset, expected in ((-1, below), (0, tie), (1, above)):
                bits = midpoint + offset
                with self.subTest(midpoint=hex(midpoint), offset=offset):
                    self.assert_model(
                        "sse2.cvt.f64x2.f32x4",
                        {"a": vector("f64", (bits, bits | (1 << 63)))},
                        vector("f32", (expected, expected | (1 << 31), 0, 0)),
                    )

    def test_variable_shift_uses_all_64_count_bits(self):
        # Masking the count to 8/32 bits or to (width - 1) turns these into
        # small shifts. SSE2 instead clears/sign-fills each entire lane.
        for width in (16, 32, 64):
            element, lanes = f"i{width}", 128 // width
            negative = 1 << (width - 1)
            mask = (1 << width) - 1
            values = (negative, 1) * (lanes // 2)
            operations = ("sll", "srl", "sra") if width != 64 else ("sll", "srl")
            for operation in operations:
                expected = (mask, 0) * (lanes // 2) if operation == "sra" else (0,) * lanes
                for count in (width, width + 1, 1 << 32, (1 << 32) + 1,
                              1 << 63, (1 << 64) - 1):
                    with self.subTest(width=width, operation=operation, count=hex(count)):
                        self.assert_model(
                            f"sse2.{operation}.{element}x{lanes}.vector-count",
                            {"a": vector(element, values), "count": vector("u64", (count, 0))},
                            vector(element, expected),
                        )

    def test_variable_shift_ignores_upper_count_lane(self):
        for width in (16, 32, 64):
            element, lanes = f"i{width}", 128 // width
            values = tuple(range(1, lanes + 1))
            operations = ("sll", "srl", "sra") if width != 64 else ("sll", "srl")
            for operation in operations:
                with self.subTest(width=width, operation=operation):
                    self.assert_model(
                        f"sse2.{operation}.{element}x{lanes}.vector-count",
                        {"a": vector(element, values),
                         "count": vector("u64", (0, (1 << 64) - 1))},
                        vector(element, values),
                    )

    def test_madd_unique_signed_overflow_wraps_without_saturating(self):
        self.assert_model(
            "sse2.madd.i16x8.default",
            {"a": vector("i16", (0x8000, 0x8000, 0x8000, 0x8000, 1, 2, 0xFFFF, 1)),
             "b": vector("i16", (0x8000, 0x8000, 0x8000, 0x7FFF, 3, 4, 1, 1))},
            vector("i32", (0x80000000, 0x00008000, 11, 0)),
        )

    def test_bitcasts_preserve_every_bit_across_lane_boundaries(self):
        for source, target in (("f32", "f64"), ("f64", "f32"), ("f32", "i32"),
                               ("i32", "f32"), ("f64", "i64"), ("i64", "f64")):
            sw, tw = int(source[1:]), int(target[1:])
            for position in range(128):
                a, expected = [0] * (128 // sw), [0] * (128 // tw)
                a[position // sw] = 1 << (position % sw)
                expected[position // tw] = 1 << (position % tw)
                with self.subTest(source=source, target=target, bit=position):
                    self.assert_model(f"sse2.cast.{source}x{128 // sw}.{target}x{128 // tw}",
                                      {"a": vector(source, tuple(a))}, vector(target, tuple(expected)))

    def test_unaligned_stores_preserve_guards_and_unrelated_buffers(self):
        for element, lanes in (("f32", 4), ("f64", 2), ("i32", 4)):
            byte_width = int(element[1:]) // 8
            # Unique bytes reveal endian reversal and lane swaps independently.
            payload = bytes(range(0x80, 0x90))
            values = tuple(int.from_bytes(payload[i:i + byte_width], "little")
                           for i in range(0, 16, byte_width))
            for offset in range(16):
                initial = bytes(range(40))
                expected = initial[:offset] + payload + initial[offset + 16:]
                with self.subTest(element=element, offset=offset):
                    self.assert_model(
                        f"sse2.storeu.{element}x{lanes}.default",
                        {"destination": {"buffer": "dst", "offset": offset}, "a": vector(element, values)},
                        None,
                        buffers={"dst": {"alignment": 1, "bytes": "0x" + initial.hex()},
                                 "untouched": {"alignment": 1, "bytes": "0xdeadbeef"}},
                        observed={"buffers": {"dst": {"byte_offset": 0, "bytes": "0x" + expected.hex()},
                                              "untouched": {"byte_offset": 0, "bytes": "0xdeadbeef"}}},
                    )


if __name__ == "__main__":
    unittest.main()
