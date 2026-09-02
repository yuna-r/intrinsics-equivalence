"""Development generator and executable model for _mm_cvtps_epi32."""

from __future__ import annotations

import math
import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvt.f32x4.i32x4"
MINIMUM_COUNTS = {"standard": 8}
INDEFINITE = 0x80000000


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0x00000000, 0x80000000, 0x3F800000, 0xBF800000),
        (0x3FB33333, 0xBFB33333, 0x3FC00000, 0x40200000),
        (0xBFC00000, 0xC0200000, 0x40700000, 0xC0700000),
        (0x4EFFFFFF, 0xCF000000, 0x4F000000, 0xCF000001),
        (0x7F800000, 0xFF800000, 0x7FC00042, 0x7F800001),
        (0x00000001, 0x80000001, 0x007FFFFF, 0x807FFFFF),
        (0x3EFFFFFF, 0xBEFFFFFF, 0x3F000000, 0xBF000000),
        (0x4B000001, 0xCB000001, 0x4AFFFFFF, 0xCAFFFFFF),
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
                "a": vector(
                    "f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))
                )
            },
        }


def _nearest_i32(bits: int) -> int:
    value = struct.unpack(">f", bits.to_bytes(4, "big"))[0]
    if not math.isfinite(value):
        return INDEFINITE
    rounded = round(value)
    if rounded < -(1 << 31) or rounded > (1 << 31) - 1:
        return INDEFINITE
    return rounded & 0xFFFFFFFF


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    return {
        "return": vector(
            "i32", tuple(_nearest_i32(int(str(bits), 16)) for bits in lanes)
        )
    }
