"""Deterministic comparison of two validated IOITF result records.

This module deliberately compares the canonical, architecture-independent
values from :mod:`ioitf.records`; it never interprets native vector layouts.
The ordering and atom counting implemented here are the schema-version-1
rules from specification sections 13 and 15.1.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import math
import re
import struct
from typing import Literal, TypeAlias

from .canonical import JSONValue, MAX_SAFE_INTEGER, require_object, utf16_sort_key
from .cases import CaseDefinition
from .errors import ValidationError
from .records import FP_EXCEPTION_ORDER, validate_input_record, validate_result_record


ComparisonOutcome: TypeAlias = Literal["match", "mismatch", "not_comparable"]
FirstDifference: TypeAlias = dict[str, JSONValue]

_FLOAT_ELEMENTS = {"f32", "f64"}
_DECIMAL_PATTERN = re.compile(r"^[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$")


@dataclass(frozen=True)
class ComparisonResult:
    """The deterministic disposition of one Intel/POWER result pair.

    ``first_difference`` is already in the shape required by
    ``failure.json``.  A pair with the same non-``ok`` status is
    ``not_comparable`` rather than a match and therefore has no mismatch
    atoms or normal failure-bundle difference.
    """

    outcome: ComparisonOutcome
    mismatch_count: int
    first_difference: FirstDifference | None
    reason: str | None = None

    @property
    def matched(self) -> bool:
        return self.outcome == "match"

    @property
    def comparable(self) -> bool:
        return self.outcome != "not_comparable"

    def failure_fields(self) -> dict[str, JSONValue]:
        """Return the fields copied into ``failure.json`` for a mismatch."""

        if self.outcome != "mismatch" or self.first_difference is None:
            raise ValueError("failure fields exist only for a mismatch")
        return {
            "first_difference": self.first_difference,
            "mismatch_count": self.mismatch_count,
        }


@dataclass(frozen=True)
class _FloatValue:
    element: str
    bits_text: str
    bits: int
    width: int
    exponent_bits: int
    fraction_bits: int
    sign: int
    exponent: int
    fraction: int

    @property
    def quiet_bit(self) -> int:
        return 1 << (self.fraction_bits - 1)

    @property
    def exponent_max(self) -> int:
        return (1 << self.exponent_bits) - 1

    @property
    def is_nan(self) -> bool:
        return self.exponent == self.exponent_max and self.fraction != 0

    @property
    def is_infinite(self) -> bool:
        return self.exponent == self.exponent_max and self.fraction == 0

    @property
    def is_zero(self) -> bool:
        return self.exponent == 0 and self.fraction == 0

    @property
    def is_finite(self) -> bool:
        return self.exponent != self.exponent_max

    @property
    def is_quiet_nan(self) -> bool:
        return self.is_nan and bool(self.fraction & self.quiet_bit)

    @property
    def nan_payload(self) -> int:
        # The quiet/signaling discriminator is not part of the payload.
        return self.fraction & (self.quiet_bit - 1)

    @property
    def classification(self) -> str:
        if self.is_nan:
            return "quiet_nan" if self.is_quiet_nan else "signaling_nan"
        if self.is_infinite:
            return "negative_infinity" if self.sign else "positive_infinity"
        if self.is_zero:
            return "negative_zero" if self.sign else "positive_zero"
        if self.exponent == 0:
            return "subnormal"
        return "normal"

    def exact_fraction(self) -> Fraction:
        if not self.is_finite:
            raise ValueError("NaN and infinity have no finite rational value")
        if self.exponent == 0:
            significand = self.fraction
            binary_exponent = 1 - self.bias - self.fraction_bits
        else:
            significand = (1 << self.fraction_bits) | self.fraction
            binary_exponent = self.exponent - self.bias - self.fraction_bits
        if binary_exponent >= 0:
            value = Fraction(significand << binary_exponent, 1)
        else:
            value = Fraction(significand, 1 << -binary_exponent)
        return -value if self.sign else value

    @property
    def bias(self) -> int:
        return (1 << (self.exponent_bits - 1)) - 1

    def ulp_key(self) -> int:
        sign_bit = 1 << (self.width - 1)
        maximum = (1 << self.width) - 1
        return maximum - self.bits if self.sign else self.bits | sign_bit

    def binary64(self) -> float:
        if self.element == "f32":
            return float(struct.unpack(">f", self.bits.to_bytes(4, "big"))[0])
        return struct.unpack(">d", self.bits.to_bytes(8, "big"))[0]


@dataclass(frozen=True)
class _ReturnDifference:
    lane: int | None
    intel: str
    openpower: str
    diagnostic: dict[str, JSONValue] | None


@dataclass(frozen=True)
class _MemoryViolation:
    runner: Literal["intel", "openpower"]
    buffer: str
    byte_offset: int
    before: int
    after: int


@dataclass(frozen=True)
class _BufferDifference:
    buffer: str
    byte_offset: int
    intel: int
    openpower: int


def _parse_float(bits_text: str, element: str) -> _FloatValue:
    if element == "f32":
        width, exponent_bits, fraction_bits = 32, 8, 23
    elif element == "f64":
        width, exponent_bits, fraction_bits = 64, 11, 52
    else:
        raise ValidationError(f"comparison: {element!r} is not a floating-point element")
    expected_digits = width // 4
    if not re.fullmatch(rf"0x[0-9a-f]{{{expected_digits}}}", bits_text):
        raise ValidationError(f"comparison: invalid {element} bit string {bits_text!r}")
    bits = int(bits_text[2:], 16)
    fraction_mask = (1 << fraction_bits) - 1
    exponent_mask = (1 << exponent_bits) - 1
    return _FloatValue(
        element=element,
        bits_text=bits_text,
        bits=bits,
        width=width,
        exponent_bits=exponent_bits,
        fraction_bits=fraction_bits,
        sign=bits >> (width - 1),
        exponent=(bits >> fraction_bits) & exponent_mask,
        fraction=bits & fraction_mask,
    )


def _nan_equal(
    intel: _FloatValue,
    openpower: _FloatValue,
    comparison: dict[str, JSONValue],
) -> bool:
    policy = require_object(comparison["nan"], "case.comparison.nan")
    if policy["both_nan"] == "unequal":
        return False
    if policy["quiet_signaling"] == "match" and (
        intel.is_quiet_nan != openpower.is_quiet_nan
    ):
        return False
    if policy["payload"] == "match" and intel.nan_payload != openpower.nan_payload:
        return False
    if policy["sign"] == "match" and intel.sign != openpower.sign:
        return False
    return True


def _ulp_distance(
    intel: _FloatValue,
    openpower: _FloatValue,
    *,
    signed_zero: str,
) -> int:
    distance = abs(intel.ulp_key() - openpower.ulp_key())
    if signed_zero == "equal" and intel.sign != openpower.sign:
        distance = max(distance - 1, 0)
    return distance


def _bounded_exponent(text: str, *, limit: int, location: str) -> int:
    if not text:
        return 0
    sign = -1 if text.startswith("-") else 1
    digits = text[1:] if text[:1] in {"+", "-"} else text
    digits = digits.lstrip("0") or "0"
    limit_text = str(limit)
    if len(digits) > len(limit_text) or (
        len(digits) == len(limit_text) and digits > limit_text
    ):
        return sign * (limit + 1)
    try:
        return sign * int(digits)
    except ValueError as exc:
        raise ValidationError(f"{location}: invalid decimal exponent") from exc


def _fraction_decimal_order(value: Fraction) -> int:
    """Return floor(log10(value)) without floating-point conversion."""

    if value <= 0:
        raise ValueError("decimal order requires a positive fraction")
    numerator_digits = len(str(value.numerator))
    denominator_digits = len(str(value.denominator))
    estimate = numerator_digits - denominator_digits
    if estimate >= 0:
        at_estimate = value.numerator >= value.denominator * (10**estimate)
    else:
        at_estimate = value.numerator * (10 ** (-estimate)) >= value.denominator
    return estimate if at_estimate else estimate - 1


def _fraction_le_decimal(value: Fraction, text: str, location: str) -> bool:
    """Compare a non-negative rational with an arbitrary-size decimal exactly."""

    if not _DECIMAL_PATTERN.fullmatch(text):
        raise ValidationError(f"{location}: invalid non-negative decimal")
    significand_text, separator, exponent_text = text.lower().partition("e")
    whole, point, fractional = significand_text.partition(".")
    raw_digits = whole + (fractional if point else "")
    significant = raw_digits.lstrip("0")
    if not significant:
        return value <= 0
    trailing = len(significant) - len(significant.rstrip("0"))
    digits = significant[:-trailing] if trailing else significant
    limit = len(raw_digits) + 10_000
    explicit_exponent = _bounded_exponent(
        exponent_text if separator else "",
        limit=limit,
        location=location,
    )
    power = explicit_exponent - len(fractional) + trailing
    if value <= 0:
        return True
    decimal_order = len(digits) - 1 + power
    value_order = _fraction_decimal_order(value)
    if decimal_order != value_order:
        return decimal_order > value_order
    try:
        coefficient = int(Decimal(digits))
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"{location}: cannot interpret decimal coefficient") from exc
    if power >= 0:
        return value.numerator <= coefficient * (10**power) * value.denominator
    return value.numerator * (10 ** (-power)) <= coefficient * value.denominator


def _float_equal(
    intel: _FloatValue,
    openpower: _FloatValue,
    comparison: dict[str, JSONValue],
) -> bool:
    mode = str(comparison["mode"])
    if mode == "bit_exact":
        return intel.bits == openpower.bits

    # ieee_equal is accepted here as a convenience alias for callers of the
    # low-level comparator.  The schema validator correctly accepts only the
    # specification spelling, ieee_value.
    if mode == "ieee_equal":
        mode = "ieee_value"

    if intel.is_nan or openpower.is_nan:
        return intel.is_nan and openpower.is_nan and _nan_equal(
            intel, openpower, comparison
        )
    if intel.is_infinite or openpower.is_infinite:
        return (
            intel.is_infinite
            and openpower.is_infinite
            and intel.sign == openpower.sign
        )
    if intel.is_zero and openpower.is_zero:
        return comparison["signed_zero"] == "equal" or intel.sign == openpower.sign

    if mode == "classification":
        intel_class = "zero" if intel.is_zero else (
            "subnormal" if intel.exponent == 0 else "normal"
        )
        power_class = "zero" if openpower.is_zero else (
            "subnormal" if openpower.exponent == 0 else "normal"
        )
        return intel_class == power_class and (
            intel_class == "zero" or intel.sign == openpower.sign
        )
    if mode == "ieee_value":
        return intel.exact_fraction() == openpower.exact_fraction()
    if mode == "ulp":
        maximum = int(str(comparison["max_ulps"]))
        return _ulp_distance(
            intel,
            openpower,
            signed_zero=str(comparison["signed_zero"]),
        ) <= maximum
    if mode == "abs_rel":
        a = intel.exact_fraction()
        b = openpower.exact_fraction()
        difference = abs(a - b)
        magnitude = max(abs(a), abs(b))
        if _fraction_le_decimal(
            difference,
            str(comparison["abs_tolerance"]),
            "case.comparison.abs_tolerance",
        ):
            return True
        if magnitude == 0:
            return False
        return _fraction_le_decimal(
            difference / magnitude,
            str(comparison["rel_tolerance"]),
            "case.comparison.rel_tolerance",
        )
    raise ValidationError(f"comparison: unsupported floating-point mode {mode!r}")


def _ecmascript_number_token(value: float) -> str:
    """Format a finite nonzero binary64 like ECMAScript Number::toString.

    CPython and ECMAScript use the same shortest-roundtrip selection.  Their
    presentation thresholds differ, so the shortest digits from ``repr`` are
    rearranged according to RFC 8785 / ECMAScript's ``k`` and ``n`` rules.
    """

    if not math.isfinite(value) or value == 0.0:
        raise ValueError("decimal diagnostics require a finite nonzero value")
    sign = "-" if value < 0 else ""
    text = repr(abs(value)).lower()
    mantissa, marker, exponent_text = text.partition("e")
    exponent = int(exponent_text) if marker else 0
    whole, point, fractional = mantissa.partition(".")
    combined = whole + (fractional if point else "")
    decimal_position = len(whole) + exponent

    leading = len(combined) - len(combined.lstrip("0"))
    digits = combined[leading:]
    decimal_position -= leading
    digits = digits.rstrip("0")
    if not digits:
        raise AssertionError("nonzero float lost all significant digits")

    k = len(digits)
    n = decimal_position
    if k <= n <= 21:
        body = digits + ("0" * (n - k))
    elif 0 < n <= 21:
        body = digits[:n] + "." + digits[n:]
    elif -6 < n <= 0:
        body = "0." + ("0" * -n) + digits
    else:
        body = digits[0]
        if k > 1:
            body += "." + digits[1:]
        scientific_exponent = n - 1
        body += "e" + ("+" if scientific_exponent >= 0 else "") + str(
            scientific_exponent
        )
    return sign + body


def _float_diagnostic(
    intel: _FloatValue,
    openpower: _FloatValue,
    comparison: dict[str, JSONValue],
) -> dict[str, JSONValue]:
    def role(value: _FloatValue) -> dict[str, JSONValue]:
        result: dict[str, JSONValue] = {"classification": value.classification}
        if value.is_finite and not value.is_zero:
            result["decimal"] = _ecmascript_number_token(value.binary64())
        return result

    diagnostic: dict[str, JSONValue] = {
        "intel": role(intel),
        "openpower": role(openpower),
    }
    if (
        comparison["mode"] == "ulp"
        and intel.is_finite
        and openpower.is_finite
        and not (intel.is_zero and openpower.is_zero)
    ):
        diagnostic["ulp_distance"] = str(
            _ulp_distance(
                intel,
                openpower,
                signed_zero=str(comparison["signed_zero"]),
            )
        )
    return diagnostic


def compare_float_bits(
    intel_bits: str,
    openpower_bits: str,
    *,
    element: Literal["f32", "f64"],
    comparison: dict[str, JSONValue],
) -> bool:
    """Compare one floating-point lane using a validated comparison object."""

    return _float_equal(
        _parse_float(intel_bits, element),
        _parse_float(openpower_bits, element),
        comparison,
    )


def _return_differences(
    case: CaseDefinition,
    intel_observed: dict[str, JSONValue],
    openpower_observed: dict[str, JSONValue],
) -> list[_ReturnDifference]:
    contract = require_object(case.signature["return"], f"case {case.id}.signature.return")
    result_type = str(contract["type"])
    if result_type == "void":
        return []

    intel_return = require_object(intel_observed["return"], "intel.observed.return")
    power_return = require_object(openpower_observed["return"], "openpower.observed.return")
    element = str(contract["element"])
    comparison = case.comparison

    if result_type == "scalar":
        pairs: list[tuple[int | None, str, str]] = [
            (None, str(intel_return["bits"]), str(power_return["bits"]))
        ]
    else:
        intel_lanes = intel_return["lanes"]
        power_lanes = power_return["lanes"]
        assert isinstance(intel_lanes, list) and isinstance(power_lanes, list)
        pairs = [
            (index, str(intel_lanes[index]), str(power_lanes[index]))
            for index in range(len(intel_lanes))
        ]

    differences: list[_ReturnDifference] = []
    for lane, intel_bits, power_bits in pairs:
        diagnostic: dict[str, JSONValue] | None = None
        if element in _FLOAT_ELEMENTS:
            intel_float = _parse_float(intel_bits, element)
            power_float = _parse_float(power_bits, element)
            equal = _float_equal(intel_float, power_float, comparison)
            if not equal:
                diagnostic = _float_diagnostic(intel_float, power_float, comparison)
        else:
            equal = intel_bits == power_bits
        if not equal:
            differences.append(
                _ReturnDifference(lane, intel_bits, power_bits, diagnostic)
            )
    return differences


def _hex_bytes(value: JSONValue, location: str) -> bytes:
    if not isinstance(value, str) or not re.fullmatch(r"0x(?:[0-9a-f]{2})*", value):
        raise ValidationError(f"{location}: invalid canonical byte string")
    return bytes.fromhex(value[2:])


def _merge_ranges(ranges: list[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    if not ranges:
        return ()
    merged: list[list[int]] = []
    for start, end in sorted(ranges):
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return tuple((start, end) for start, end in merged)


def _allowed_write_ranges(
    case: CaseDefinition,
    input_record: dict[str, JSONValue],
) -> dict[str, tuple[tuple[int, int], ...]]:
    if "memory_contract" not in case.data:
        return {}
    operands = require_object(input_record["operands"], "input.operands")
    buffers = require_object(input_record["buffers"], "input.buffers")
    memory = require_object(case.data["memory_contract"], f"case {case.id}.memory_contract")
    by_buffer: dict[str, list[tuple[int, int]]] = {buffer_id: [] for buffer_id in buffers}
    arguments = case.signature["arguments"]
    assert isinstance(arguments, list)
    for raw_argument in arguments:
        argument = require_object(raw_argument, f"case {case.id}.signature.arguments")
        if argument["type"] != "pointer":
            continue
        name = str(argument["name"])
        pointer = require_object(operands[name], f"input.operands.{name}")
        buffer_id = str(pointer["buffer"])
        pointer_offset = int(pointer["offset"])
        contract = require_object(memory[name], f"case {case.id}.memory_contract.{name}")
        write_ranges = contract["write_ranges"]
        assert isinstance(write_ranges, list)
        for raw_range in write_ranges:
            item = require_object(raw_range, f"case {case.id}.memory_contract.{name}.write_ranges")
            start = pointer_offset + int(item["offset"])
            by_buffer[buffer_id].append((start, start + int(item["byte_length"])))
    return {buffer_id: _merge_ranges(ranges) for buffer_id, ranges in by_buffer.items()}


def _in_ranges(offset: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    # Range counts are normally tiny, and scanning bytes in increasing order
    # makes this linear in practical contracts without expanding ranges.
    for start, end in ranges:
        if offset < start:
            return False
        if offset < end:
            return True
    return False


def _observed_buffers(observed: dict[str, JSONValue]) -> dict[str, bytes]:
    raw_buffers = require_object(observed["buffers"], "result.observed.buffers")
    result: dict[str, bytes] = {}
    for buffer_id, raw in raw_buffers.items():
        item = require_object(raw, f"result.observed.buffers.{buffer_id}")
        result[buffer_id] = _hex_bytes(
            item["bytes"], f"result.observed.buffers.{buffer_id}.bytes"
        )
    return result


def _memory_differences(
    case: CaseDefinition,
    input_record: dict[str, JSONValue],
    intel_observed: dict[str, JSONValue],
    openpower_observed: dict[str, JSONValue],
) -> tuple[list[_MemoryViolation], list[_BufferDifference]]:
    if "buffers" not in input_record:
        return [], []
    raw_input_buffers = require_object(input_record["buffers"], "input.buffers")
    initial = {
        buffer_id: _hex_bytes(
            require_object(raw, f"input.buffers.{buffer_id}")["bytes"],
            f"input.buffers.{buffer_id}.bytes",
        )
        for buffer_id, raw in raw_input_buffers.items()
    }
    intel = _observed_buffers(intel_observed)
    openpower = _observed_buffers(openpower_observed)
    allowed = _allowed_write_ranges(case, input_record)
    violations: list[_MemoryViolation] = []
    violation_positions: set[tuple[str, int]] = set()
    for runner, final in (("intel", intel), ("openpower", openpower)):
        for buffer_id in sorted(initial, key=utf16_sort_key):
            for offset, (before, after) in enumerate(zip(initial[buffer_id], final[buffer_id])):
                if before != after and not _in_ranges(offset, allowed.get(buffer_id, ())):
                    violations.append(
                        _MemoryViolation(
                            runner=runner,  # type: ignore[arg-type]
                            buffer=buffer_id,
                            byte_offset=offset,
                            before=before,
                            after=after,
                        )
                    )
                    violation_positions.add((buffer_id, offset))

    differences: list[_BufferDifference] = []
    for buffer_id in sorted(initial, key=utf16_sort_key):
        for offset, (intel_byte, power_byte) in enumerate(
            zip(intel[buffer_id], openpower[buffer_id])
        ):
            if (
                intel_byte != power_byte
                and (buffer_id, offset) not in violation_positions
            ):
                differences.append(
                    _BufferDifference(buffer_id, offset, intel_byte, power_byte)
                )
    return violations, differences


def _return_first(difference: _ReturnDifference) -> FirstDifference:
    result: FirstDifference = {
        "intel": difference.intel,
        "kind": "return",
        "openpower": difference.openpower,
    }
    if difference.lane is not None:
        result["lane"] = difference.lane
    if difference.diagnostic is not None:
        result["diagnostic"] = difference.diagnostic
    return result


def _memory_first(violation: _MemoryViolation) -> FirstDifference:
    return {
        "after": f"0x{violation.after:02x}",
        "before": f"0x{violation.before:02x}",
        "buffer": violation.buffer,
        "byte_offset": violation.byte_offset,
        "kind": "memory_contract",
        "runner": violation.runner,
    }


def _buffer_first(difference: _BufferDifference) -> FirstDifference:
    return {
        "buffer": difference.buffer,
        "byte_offset": difference.byte_offset,
        "intel": f"0x{difference.intel:02x}",
        "kind": "buffer",
        "openpower": f"0x{difference.openpower:02x}",
    }


def compare_result_records(
    case: CaseDefinition,
    input_record: dict[str, JSONValue],
    intel_result: dict[str, JSONValue],
    openpower_result: dict[str, JSONValue],
    *,
    validate: bool = True,
) -> ComparisonResult:
    """Compare one Intel/POWER result pair using ``case`` and ``input_record``.

    With the default ``validate=True``, malformed inputs and results raise
    :class:`~ioitf.errors.ValidationError` instead of being reported as a SUT
    mismatch.  This preserves the specification's distinction between an
    invalid result artifact and a valid semantic difference.
    """

    if validate:
        validate_input_record(input_record, case)
        validate_result_record(
            intel_result, case, role="intel", input_record=input_record
        )
        validate_result_record(
            openpower_result, case, role="openpower", input_record=input_record
        )
    input_id = input_record.get("input_id")
    if intel_result.get("input_id") != input_id:
        raise ValidationError("intel result input_id does not match the input record")
    if openpower_result.get("input_id") != input_id:
        raise ValidationError("openpower result input_id does not match the input record")
    if intel_result.get("case_id") != case.id or openpower_result.get("case_id") != case.id:
        raise ValidationError("result case_id does not match the case definition")

    intel_status = str(intel_result["status"])
    power_status = str(openpower_result["status"])
    if intel_status != power_status:
        return ComparisonResult(
            outcome="mismatch",
            mismatch_count=1,
            first_difference={
                "intel": intel_status,
                "kind": "status",
                "openpower": power_status,
            },
            reason="status_mismatch",
        )
    if intel_status != "ok":
        return ComparisonResult(
            outcome="not_comparable",
            mismatch_count=0,
            first_difference=None,
            reason=f"both_{intel_status}",
        )

    intel_observed = require_object(intel_result["observed"], "intel.observed")
    power_observed = require_object(openpower_result["observed"], "openpower.observed")

    memory_violations, buffer_differences = _memory_differences(
        case, input_record, intel_observed, power_observed
    )
    return_differences = _return_differences(case, intel_observed, power_observed)

    intel_flags = intel_observed.get("fp_exceptions", [])
    power_flags = power_observed.get("fp_exceptions", [])
    assert isinstance(intel_flags, list) and isinstance(power_flags, list)
    intel_flag_set = set(intel_flags)
    power_flag_set = set(power_flags)
    exception_count = sum(
        (flag in intel_flag_set) != (flag in power_flag_set)
        for flag in FP_EXCEPTION_ORDER
    )

    mismatch_count = (
        len(memory_violations)
        + len(return_differences)
        + len(buffer_differences)
        + exception_count
    )
    if mismatch_count > MAX_SAFE_INTEGER:
        raise ValidationError("comparison mismatch_count exceeds the JSON safe integer range")
    if mismatch_count == 0:
        return ComparisonResult("match", 0, None)

    # Section 15.1 fixes this exact priority after status comparison.
    if memory_violations:
        first = _memory_first(memory_violations[0])
    elif return_differences:
        first = _return_first(return_differences[0])
    elif buffer_differences:
        first = _buffer_first(buffer_differences[0])
    else:
        first = {
            "intel": list(intel_flags),
            "kind": "fp_exceptions",
            "openpower": list(power_flags),
        }
    return ComparisonResult("mismatch", mismatch_count, first, "value_mismatch")


# Concise public spelling for coordinator and test code.
compare_results = compare_result_records


__all__ = [
    "ComparisonOutcome",
    "ComparisonResult",
    "compare_float_bits",
    "compare_result_records",
    "compare_results",
]
