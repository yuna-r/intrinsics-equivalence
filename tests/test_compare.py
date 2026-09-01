from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest


PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / "src"))

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition, validate_case_definition
from ioitf.compare import compare_float_bits, compare_results
from ioitf.records import derive_input_id


def float_case(
    comparison: dict[str, JSONValue], *, observe_exceptions: bool = False
) -> CaseDefinition:
    data: dict[str, JSONValue] = {
            "comparison": comparison,
            "description": "comparison fixture",
            "environment": {
                "fp_rounding_modes": ["nearest_even"],
                "observe_fp_exceptions": observe_exceptions,
            },
            "id": "sse2.fixture.f64x2.default",
            "input_domain": {"exclude": []},
            "intel": {"required_isa": ["sse2"], "symbol": "intel_fixture"},
            "openpower": {
                "required_isa": ["power8", "vsx"],
                "symbol": "power_fixture",
            },
            "schema_version": 1,
            "signature": {
                "arguments": [
                    {"element": "f64", "lanes": 2, "name": "a", "type": "vector"}
                ],
                "return": {"element": "f64", "lanes": 2, "type": "vector"},
            },
            "tags": [],
        }
    if observe_exceptions:
        data["regressions"] = {
            "invalid-witness.v1": {
                "expected_intel": {
                    "observed": {
                        "fp_exceptions": ["invalid"],
                        "return": {
                            "element": "f64",
                            "lanes": [
                                "0x0000000000000000",
                                "0x0000000000000000",
                            ],
                        },
                    },
                    "status": "ok",
                },
                "input_id": "0" * 64,
            }
        }
    return validate_case_definition(data)


def memory_case() -> CaseDefinition:
    return validate_case_definition(
        {
            "comparison": {"mode": "bit_exact"},
            "description": "memory comparison fixture",
            "environment": {
                "fp_rounding_modes": ["nearest_even"],
                "observe_fp_exceptions": False,
            },
            "id": "sse2.fixture.memory.default",
            "input_domain": {"exclude": []},
            "intel": {"required_isa": ["sse2"], "symbol": "intel_memory"},
            "memory_contract": {
                "dst": {
                    "access": "write",
                    "read_ranges": [],
                    "required_alignment": 1,
                    "write_ranges": [{"byte_length": 1, "offset": 1}],
                }
            },
            "openpower": {
                "required_isa": ["power8", "vsx"],
                "symbol": "power_memory",
            },
            "schema_version": 1,
            "signature": {
                "arguments": [{"name": "dst", "type": "pointer"}],
                "return": {"element": "i32", "lanes": 2, "type": "vector"},
            },
            "tags": [],
        }
    )


def make_input(case: CaseDefinition, *, memory: bool = False) -> dict[str, JSONValue]:
    record: dict[str, JSONValue] = {
        "case_id": case.id,
        "environment": {"fp_mode": "ieee", "rounding": "nearest_even"},
        "generation": {"class": "structured"},
        "operands": {},
        "schema_version": 1,
        "sequence": 1,
    }
    if memory:
        record["buffers"] = {"buf0": {"alignment": 1, "bytes": "0x00010203"}}
        record["operands"] = {"dst": {"buffer": "buf0", "offset": 0}}
    else:
        record["operands"] = {
            "a": {
                "element": "f64",
                "lanes": ["0x0000000000000000", "0x0000000000000000"],
            }
        }
    record["input_id"] = derive_input_id(record)
    return record


def result(
    case: CaseDefinition,
    input_record: dict[str, JSONValue],
    role: str,
    *,
    lanes: list[str] | None = None,
    buffers: str | None = None,
    flags: list[str] | None = None,
    status: str = "ok",
) -> dict[str, JSONValue]:
    record: dict[str, JSONValue] = {
        "case_id": case.id,
        "duration_ns": 1,
        "input_id": input_record["input_id"],
        "runner": role,
        "schema_version": 1,
        "status": status,
    }
    if status != "ok":
        stage = {
            "infrastructure_error": "runner",
            "invalid_input": "input_validation",
            "runtime_error": "execution",
            "signal": "signal",
            "unsupported": "capability",
        }[status]
        record["error"] = {"code": f"fixture_{status}", "stage": stage}
        return record
    element = str(case.signature["return"]["element"])
    digits = {"f64": 16, "i32": 8}[element]
    observed: dict[str, JSONValue] = {
        "return": {
            "element": element,
            "lanes": lanes or [("0x" + ("0" * digits)), ("0x" + ("0" * digits))],
        }
    }
    if buffers is not None:
        observed["buffers"] = {
            "buf0": {"byte_offset": 0, "bytes": buffers}
        }
    if flags is not None:
        observed["fp_exceptions"] = flags
    record["observed"] = observed
    return record


NAN_IGNORE: dict[str, JSONValue] = {
    "both_nan": "equal",
    "payload": "ignore",
    "quiet_signaling": "ignore",
    "sign": "ignore",
}


class FloatLaneTests(unittest.TestCase):
    def test_nan_policy_and_signed_zero(self) -> None:
        ieee: dict[str, JSONValue] = {
            "mode": "ieee_value",
            "nan": NAN_IGNORE,
            "signed_zero": "equal",
        }
        self.assertTrue(
            compare_float_bits(
                "0x0000000000000000",
                "0x8000000000000000",
                element="f64",
                comparison=ieee,
            )
        )
        self.assertTrue(
            compare_float_bits(
                "0x7ff8000000000001",
                "0xfff8000000000002",
                element="f64",
                comparison=ieee,
            )
        )
        payload_match = copy.deepcopy(ieee)
        assert isinstance(payload_match["nan"], dict)
        payload_match["nan"]["payload"] = "match"
        self.assertFalse(
            compare_float_bits(
                "0x7ff8000000000001",
                "0x7ff8000000000002",
                element="f64",
                comparison=payload_match,
            )
        )

    def test_ulp_abs_rel_and_classification(self) -> None:
        ulp: dict[str, JSONValue] = {
            "max_ulps": "1",
            "mode": "ulp",
            "nan": NAN_IGNORE,
            "signed_zero": "equal",
        }
        self.assertTrue(
            compare_float_bits(
                "0x3ff0000000000000",
                "0x3ff0000000000001",
                element="f64",
                comparison=ulp,
            )
        )
        absolute: dict[str, JSONValue] = {
            "abs_tolerance": "0.000000000000001",
            "mode": "abs_rel",
            "nan": NAN_IGNORE,
            "rel_tolerance": "0",
            "signed_zero": "equal",
        }
        self.assertTrue(
            compare_float_bits(
                "0x3ff0000000000000",
                "0x3ff0000000000001",
                element="f64",
                comparison=absolute,
            )
        )
        classification: dict[str, JSONValue] = {
            "mode": "classification",
            "nan": NAN_IGNORE,
            "signed_zero": "equal",
        }
        self.assertTrue(
            compare_float_bits(
                "0x3ff0000000000000",
                "0x4000000000000000",
                element="f64",
                comparison=classification,
            )
        )

    def test_abs_rel_accepts_arbitrary_size_decimal_without_host_limits(self) -> None:
        comparisons = (
            ("1" * 5000, True),
            ("0." + "9" * 5000, False),
            ("1e" + "9" * 5000, True),
            ("1e-" + "9" * 5000, False),
        )
        for tolerance, expected in comparisons:
            comparison: dict[str, JSONValue] = {
                "abs_tolerance": tolerance,
                "mode": "abs_rel",
                "nan": NAN_IGNORE,
                "rel_tolerance": "0",
                "signed_zero": "equal",
            }
            with self.subTest(tolerance_length=len(tolerance), expected=expected):
                self.assertEqual(
                    compare_float_bits(
                        "0x3ff0000000000000",
                        "0x4000000000000000",
                        element="f64",
                        comparison=comparison,
                    ),
                    expected,
                )


class RecordComparisonTests(unittest.TestCase):
    def test_status_difference_and_same_non_ok(self) -> None:
        case = float_case({"mode": "bit_exact"})
        input_record = make_input(case)
        intel = result(case, input_record, "intel", status="unsupported")
        power = result(case, input_record, "openpower", status="runtime_error")
        different = compare_results(case, input_record, intel, power)
        self.assertEqual(different.outcome, "mismatch")
        self.assertEqual(different.mismatch_count, 1)
        self.assertEqual(different.first_difference["kind"], "status")  # type: ignore[index]

        power = result(case, input_record, "openpower", status="unsupported")
        same = compare_results(case, input_record, intel, power)
        self.assertEqual(same.outcome, "not_comparable")
        self.assertFalse(same.matched)
        self.assertEqual(same.mismatch_count, 0)
        self.assertIsNone(same.first_difference)

    def test_memory_contract_has_priority_and_is_not_double_counted(self) -> None:
        case = memory_case()
        input_record = make_input(case, memory=True)
        intel = result(
            case,
            input_record,
            "intel",
            lanes=["0x00000001", "0x00000000"],
            buffers="0xff010203",
        )
        power = result(
            case,
            input_record,
            "openpower",
            lanes=["0x00000000", "0x00000000"],
            buffers="0x00010203",
        )
        compared = compare_results(case, input_record, intel, power)
        # One contract atom plus one return-lane atom.  The role buffer
        # difference at offset zero is excluded because it is already in V.
        self.assertEqual(compared.mismatch_count, 2)
        self.assertEqual(
            compared.first_difference,
            {
                "after": "0xff",
                "before": "0x00",
                "buffer": "buf0",
                "byte_offset": 0,
                "kind": "memory_contract",
                "runner": "intel",
            },
        )

    def test_allowed_buffer_difference_and_exception_atoms(self) -> None:
        case = memory_case()
        input_record = make_input(case, memory=True)
        intel = result(case, input_record, "intel", buffers="0x00ff0203")
        power = result(case, input_record, "openpower", buffers="0x00ee0203")
        compared = compare_results(case, input_record, intel, power)
        self.assertEqual(compared.mismatch_count, 1)
        self.assertEqual(compared.first_difference["kind"], "buffer")  # type: ignore[index]
        self.assertEqual(compared.first_difference["byte_offset"], 1)  # type: ignore[index]

        fp_case = float_case({"mode": "bit_exact"}, observe_exceptions=True)
        fp_input = make_input(fp_case)
        intel_fp = result(
            fp_case,
            fp_input,
            "intel",
            flags=["invalid", "inexact"],
        )
        power_fp = result(
            fp_case,
            fp_input,
            "openpower",
            flags=["overflow", "inexact"],
        )
        fp_compared = compare_results(fp_case, fp_input, intel_fp, power_fp)
        self.assertEqual(fp_compared.mismatch_count, 2)
        self.assertEqual(
            fp_compared.first_difference["kind"],  # type: ignore[index]
            "fp_exceptions",
        )

    def test_large_ulp_distance_is_a_decimal_string(self) -> None:
        case = float_case(
            {
                "max_ulps": "0",
                "mode": "ulp",
                "nan": NAN_IGNORE,
                "signed_zero": "distinct",
            }
        )
        input_record = make_input(case)
        intel = result(
            case,
            input_record,
            "intel",
            lanes=["0x3ff0000000000000", "0x0000000000000000"],
        )
        power = result(
            case,
            input_record,
            "openpower",
            lanes=["0xbff0000000000000", "0x0000000000000000"],
        )
        compared = compare_results(case, input_record, intel, power)
        self.assertEqual(compared.mismatch_count, 1)
        assert compared.first_difference is not None
        diagnostic = compared.first_difference["diagnostic"]
        assert isinstance(diagnostic, dict)
        self.assertEqual(diagnostic["ulp_distance"], "9214364837600034817")
        self.assertIsInstance(diagnostic["ulp_distance"], str)


if __name__ == "__main__":
    unittest.main()
