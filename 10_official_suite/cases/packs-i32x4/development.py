"""Development generator and executable model for _mm_packs_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.packs.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 0xFFFFFFFF, 0x7FFF), (0x8000, 0xFFFF8000, 0xFFFF7FFF, 0x80000000)),
        ((0x7FFFFFFF, 0x00007FFE, 0x00008001, 0xFFFF8001), (0xFFFFFFFF, 0, 0x00010000, 0xFFFF0000)),
        ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333), (0x11111111, 0x22222222, 0x44444444, 0x88888888)),
        ((0x00007FFF,) * 4, (0xFFFF8000,) * 4),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"a": vector("i32", a), "b": vector("i32", b)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {
                "a": vector("i32", tuple(random.next() & MASK32 for _ in range(4))),
                "b": vector("i32", tuple(random.next() & MASK32 for _ in range(4))),
            },
        }


def _signed(bits: str, width: int) -> int:
    value = int(bits, 16)
    return value - (1 << width) if value & (1 << (width - 1)) else value


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    a = left["lanes"]
    b = right["lanes"]
    assert isinstance(a, list) and isinstance(b, list)
    values = [_signed(str(bits), 32) for bits in [*a, *b]]
    lanes = [f"0x{max(-32768, min(32767, value)) & 0xFFFF:04x}" for value in values]
    return {"return": {"element": "i16", "lanes": lanes}}
