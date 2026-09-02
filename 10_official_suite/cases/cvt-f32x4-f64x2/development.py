"""Development generator and executable model for _mm_cvtps_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvt.f32x4.f64x2"
MINIMUM_COUNTS = {"standard": 10}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0x00000000, 0x80000000, 0x7FC00001, 0xFFC00001),
        (0x3F800000, 0xC0200000, 0xAAAAAAAA, 0x55555555),
        (0x00000001, 0x80000001, 0, 0),
        (0x007FFFFF, 0x807FFFFF, 0, 0),
        (0x00800000, 0x80800000, 0, 0),
        (0x7F7FFFFF, 0xFF7FFFFF, 0, 0),
        (0x7F800000, 0xFF800000, 0, 0),
        (0x7FC00042, 0xFFC00043, 0, 0),
        (0x7F800001, 0xFF800002, 0, 0),
        (0x3EAAAAAB, 0xBEAAAAAB, 0x7F800001, 0xFF800002),
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"a": vector("f32", values)},
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
            "operands": {
                "a": vector("f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4)))
            },
        }


def _widen(bits: int) -> int:
    sign = (bits >> 31) << 63
    exponent = (bits >> 23) & 0xFF
    fraction = bits & 0x7FFFFF
    if exponent == 0xFF:
        if fraction == 0:
            return sign | 0x7FF0000000000000
        return sign | 0x7FF0000000000000 | (fraction << 29) | (1 << 51)
    if exponent != 0:
        return sign | ((exponent + 896) << 52) | (fraction << 29)
    if fraction == 0:
        return sign
    leading = fraction.bit_length() - 1
    return sign | ((leading + 874) << 52) | (
        (fraction - (1 << leading)) << (52 - leading)
    )


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    return {
        "return": vector(
            "f64",
            (_widen(int(str(lanes[0]), 16)), _widen(int(str(lanes[1]), 16))),
        )
    }
