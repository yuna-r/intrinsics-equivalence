"""Development generator and executable model for _mm_cvtpd_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvt.f64x2.f32x4"
MINIMUM_COUNTS = {"standard": 12}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0x0000000000000000, 0x8000000000000000),
        (0x3FF0000000000000, 0xC004000000000000),
        (0x47EFFFFFE0000000, 0xC7EFFFFFE0000000),
        (0x3810000000000000, 0xB810000000000000),
        (0x380FFFFFC0000000, 0xB80FFFFFC0000000),
        (0x36A0000000000000, 0xB6A0000000000000),
        (0x3690000000000000, 0xB690000000000000),
        (0x3690000000000001, 0xB690000000000001),
        (0x3FF0000010000000, 0xBFF0000010000000),
        (0x7FF0000000000000, 0xFFF0000000000000),
        (0x7FF8000000000042, 0xFFF8000000000043),
        (0x7FF0000000000001, 0xFFF0000000000002),
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"a": vector("f64", values)},
        }
    while True:
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[random.next() % len(modes)],
            },
            "generation": {
                "algorithm": "splitmix64",
                "class": "random",
                "seed": seed_text,
            },
            "operands": {"a": vector("f64", (random.next(), random.next()))},
        }


def _round_shift(value: int, shift: int) -> int:
    if shift <= 0:
        return value << -shift
    quotient = value >> shift
    remainder = value - (quotient << shift)
    halfway = 1 << (shift - 1)
    if remainder > halfway or (remainder == halfway and quotient & 1):
        quotient += 1
    return quotient


def _narrow(bits: int) -> int:
    sign = (bits >> 63) << 31
    exponent = (bits >> 52) & 0x7FF
    fraction = bits & 0x000FFFFFFFFFFFFF
    if exponent == 0x7FF:
        if fraction == 0:
            return sign | 0x7F800000
        return sign | 0x7F800000 | (fraction >> 29) | 0x00400000
    if exponent == 0:
        return sign
    unbiased = exponent - 1023
    significand = (1 << 52) | fraction
    if unbiased > 127:
        return sign | 0x7F800000
    if unbiased >= -126:
        rounded = _round_shift(significand, 29)
        if rounded == 1 << 24:
            rounded >>= 1
            unbiased += 1
            if unbiased > 127:
                return sign | 0x7F800000
        return sign | ((unbiased + 127) << 23) | (rounded & 0x007FFFFF)
    rounded = _round_shift(significand, -unbiased - 97)
    if rounded >= 1 << 23:
        return sign | 0x00800000
    return sign | rounded


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    converted = tuple(_narrow(int(str(bits), 16)) for bits in lanes)
    return {"return": vector("f32", converted + (0, 0))}
