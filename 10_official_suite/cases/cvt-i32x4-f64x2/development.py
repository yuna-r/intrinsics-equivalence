"""Development generator and executable model for _mm_cvtepi32_pd."""

from __future__ import annotations

import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cvt.i32x4.f64x2"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 0, 0, 0),
        (1, MASK32, 0, 0),
        (0x7FFFFFFF, 0x80000000, 0, 0),
        (0x01000001, 0xFEFFFFFF, 0, 0),
        (0x40000000, 0xC0000000, 0, 0),
        (0x55555555, 0xAAAAAAAA, 0, 0),
        (0, MASK32, 0x7FFFFFFF, 0x80000000),
        (0x12345678, 0x89ABCDEF, 0xDEADBEEF, 0xCAFEBABE),
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


def _signed(bits: int) -> int:
    return bits - (1 << 32) if bits & 0x80000000 else bits


def _as_f64_bits(value: int) -> int:
    return int.from_bytes(struct.pack(">d", float(value)), "big")


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
            tuple(_as_f64_bits(_signed(int(str(bits), 16))) for bits in lanes[:2]),
        )
    }
