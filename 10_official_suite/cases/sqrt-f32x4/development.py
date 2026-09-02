"""Development generator and executable model for _mm_sqrt_ps."""

from __future__ import annotations

import math
import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.sqrt.f32x4.default"
MINIMUM_COUNTS = {"standard": 10}
EXPONENT_MASK = 0x7F800000
FRACTION_MASK = 0x007FFFFF
QUIET_BIT = 0x00400000


def _random_finite_f32_bits(random: SplitMix64) -> int:
    bits = random.next() & 0xFFFFFFFF
    if bits & EXPONENT_MASK == EXPONENT_MASK:
        bits ^= 0x00800000
    return bits


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3F800000, 0x40800000, 0x41100000, 0x41800000), "structured"),
        ((0x00000000, 0x80000000, 0x00000001, 0x00800000), "boundary"),
        ((0x80000001, 0x80800000, 0xBF800000, 0xFF7FFFFF), "boundary"),
        ((0x7F800000, 0xFF800000, 0x7F7FFFFF, 0x3F000000), "boundary"),
        ((0x7FC00042, 0xFFC00043, 0x7F800001, 0xFF800001), "boundary"),
        ((0x007FFFFF, 0x00800001, 0x3F7FFFFF, 0x3F800001), "boundary"),
        ((0x40000000, 0x40400000, 0x40A00000, 0x41200000), "boundary"),
        ((0x3EAAAAAB, 0x3F000000, 0x3FC00000, 0x40200000), "boundary"),
        ((0x4B000000, 0x4B000001, 0x7EFFFFFF, 0x7F000000), "boundary"),
        ((0x00000002, 0x00000100, 0x00010000, 0x01000000), "boundary"),
    )
    for index, (a, generation_class) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": generation_class},
            "operands": {"a": vector("f32", a)},
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
                "a": vector("f32", tuple(_random_finite_f32_bits(random) for _ in range(4)))
            },
        }


def _sqrt_bits(bits: int) -> int:
    magnitude = bits & 0x7FFFFFFF
    if bits & EXPONENT_MASK == EXPONENT_MASK and bits & FRACTION_MASK:
        return bits | QUIET_BIT
    if bits & 0x80000000 and magnitude:
        return 0xFFC00000
    if magnitude == 0 or bits == 0x7F800000:
        return bits
    value = struct.unpack(">f", bits.to_bytes(4, "big"))[0]
    return int.from_bytes(struct.pack(">f", math.sqrt(value)), "big")


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands["a"]
    assert isinstance(value, dict)
    source_lanes = value["lanes"]
    assert isinstance(source_lanes, list)
    lanes = [f"0x{_sqrt_bits(int(str(bits), 16)):08x}" for bits in source_lanes]
    return {"return": {"element": "f32", "lanes": lanes}}
