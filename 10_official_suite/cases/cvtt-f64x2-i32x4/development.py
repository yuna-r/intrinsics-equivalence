"""Development generator and executable model for _mm_cvttpd_epi32."""

from __future__ import annotations

import math
import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvtt.f64x2.i32x4"
MINIMUM_COUNTS = {"standard": 10}
INDEFINITE = 0x80000000


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0x0000000000000000, 0x8000000000000000),
        (0x3FFE666666666666, 0xBFFE666666666666),
        (0x3FF8000000000000, 0x4004000000000000),
        (0xBFF8000000000000, 0xC004000000000000),
        (0x41DFFFFFFFC00000, 0xC1E0000000000000),
        (0x41DFFFFFFFE00000, 0xC1E0000000100000),
        (0x41E0000000000000, 0xC1E0000000200000),
        (0x7FF0000000000000, 0xFFF0000000000000),
        (0x7FF8000000000042, 0x7FF0000000000001),
        (0x0000000000000001, 0x8000000000000001),
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


def _truncate_i32(bits: int) -> int:
    value = struct.unpack(">d", bits.to_bytes(8, "big"))[0]
    if not math.isfinite(value) or value < -(1 << 31) or value >= (1 << 31):
        return INDEFINITE
    return math.trunc(value) & 0xFFFFFFFF


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    converted = tuple(_truncate_i32(int(str(bits), 16)) for bits in lanes)
    return {"return": vector("i32", converted + (0, 0))}
