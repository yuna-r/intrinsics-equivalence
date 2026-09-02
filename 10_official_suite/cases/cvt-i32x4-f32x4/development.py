"""Development generator and executable model for _mm_cvtepi32_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvt.i32x4.f32x4"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 1, MASK32, 0x80000000),
        (0x7FFFFFFF, 0x80000000, 0x40000000, 0xC0000000),
        (0x00FFFFFF, 0x01000000, 0x01000001, 0x01000003),
        (0xFF000001, 0xFF000000, 0xFEFFFFFF, 0xFEFFFFFD),
        (0x7FFFFF80, 0x7FFFFF81, 0x80000080, 0x8000007F),
        (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC),
        (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
        (2, 3, 4, 5),
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"a": vector("i32", values)},
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
                "a": vector("i32", tuple(random.next() & MASK32 for _ in range(4)))
            },
        }


def _round_shift(value: int, shift: int) -> int:
    quotient = value >> shift
    remainder = value - (quotient << shift)
    halfway = 1 << (shift - 1)
    if remainder > halfway or (remainder == halfway and quotient & 1):
        quotient += 1
    return quotient


def _convert(bits: int) -> int:
    value = bits - (1 << 32) if bits & 0x80000000 else bits
    if value == 0:
        return 0
    sign = 0x80000000 if value < 0 else 0
    magnitude = -value if value < 0 else value
    leading = magnitude.bit_length() - 1
    if leading <= 23:
        rounded = magnitude << (23 - leading)
    else:
        rounded = _round_shift(magnitude, leading - 23)
        if rounded == 1 << 24:
            rounded >>= 1
            leading += 1
    return sign | ((leading + 127) << 23) | (rounded & 0x007FFFFF)


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    return {
        "return": vector("f32", tuple(_convert(int(str(bits), 16)) for bits in lanes))
    }
