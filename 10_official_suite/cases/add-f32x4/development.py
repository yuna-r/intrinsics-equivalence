"""Development generator and executable model for _mm_add_ps."""

from __future__ import annotations

import math
import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import (
    SplitMix64,
    rounding_modes,
    vector,
)


CASE_ID = "sse2.add.f32x4.default"
MINIMUM_COUNTS = {"standard": 10}


def _random_finite_f32_bits(random: SplitMix64) -> int:
    bits = random.next() & 0xFFFFFFFF
    if bits & 0x7F800000 == 0x7F800000:
        bits ^= 0x00800000
    return bits


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3F800000, 0x41200000, 0xC0000000, 0xC1200000),
         (0x40000000, 0x41A00000, 0xC0400000, 0x41A00000), "structured"),
        ((0x00000000, 0x80000000, 0x00000000, 0x80000000),
         (0x00000000, 0x80000000, 0x80000000, 0x00000000), "boundary"),
        ((0x00000001, 0x007FFFFF, 0x00800000, 0x80800000),
         (0x00000000, 0x00000001, 0x807FFFFF, 0x007FFFFF), "boundary"),
        ((0x7F7FFFFF, 0xFF7FFFFF, 0x7F7FFFFF, 0xFF7FFFFF),
         (0x7F7FFFFF, 0xFF7FFFFF, 0x3F800000, 0xBF800000), "boundary"),
        ((0x7F800000, 0xFF800000, 0x7F800000, 0xFF800000),
         (0x3F800000, 0xBF800000, 0xFF800000, 0x7F800000), "boundary"),
        ((0x7FC00042, 0x7F800001, 0xFFC00043, 0xFF800001),
         (0x3F800000, 0x40000000, 0x40400000, 0x40800000), "boundary"),
        ((0x3F800000, 0x3F800001, 0xBF800000, 0xBF800001),
         (0x33800000, 0x33800000, 0xB3800000, 0xB3800000), "boundary"),
        ((0x00800000, 0x80800000, 0x00000001, 0x80000001),
         (0x807FFFFF, 0x007FFFFF, 0x00000001, 0x80000001), "boundary"),
        ((0x4B000000, 0x4B000001, 0xCB000000, 0xCB000001),
         (0x3F800000, 0x3F800000, 0xBF800000, 0xBF800000), "boundary"),
        ((0x3EAAAAAB, 0xBEAAAAAB, 0x3F000000, 0xBF000000),
         (0x3EAAAAAB, 0xBEAAAAAB, 0x3F000000, 0xBF000000), "boundary"),
    )
    for index, (a, b, generation_class) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": generation_class},
            "operands": {"a": vector("f32", a), "b": vector("f32", b)},
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
                "a": vector("f32", tuple(_random_finite_f32_bits(random) for _ in range(4))),
                "b": vector("f32", tuple(_random_finite_f32_bits(random) for _ in range(4))),
            },
        }


def _from_bits(bits: str) -> float:
    return struct.unpack(">f", int(bits, 16).to_bytes(4, "big"))[0]


def _to_bits(value: float) -> str:
    try:
        integer = int.from_bytes(struct.pack(">f", value), "big")
    except OverflowError:
        integer = 0xFF800000 if math.copysign(1.0, value) < 0.0 else 0x7F800000
    return f"0x{integer:08x}"


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    left_lanes = left["lanes"]
    right_lanes = right["lanes"]
    assert isinstance(left_lanes, list) and isinstance(right_lanes, list)
    lanes = [
        _to_bits(_from_bits(str(a)) + _from_bits(str(b)))
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "f32", "lanes": lanes}}
