"""Development generator and executable model for _mm_packus_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.packus.i16x8.default"
MINIMUM_COUNTS = {"standard": 8}
MASK16 = 0xFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 0xFFFF, 254, 255, 256, 0x8000, 0x7FFF), (0xFFFE, 2, 253, 257, 0xFF00, 0x00FF, 0x0100, 0)),
        ((0x8000, 0x8001, 0xFFFF, 0, 1, 0x00FE, 0x00FF, 0x0100), (0xFF80, 0xFF81, 0x007F, 0x0080, 0x00FE, 0x00FF, 0x0100, 0x7FFF)),
        ((0xAAAA,) * 8, (0x5555,) * 8),
        ((0, 0xFFFF) * 4, (255, 256) * 4),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"a": vector("i16", a), "b": vector("i16", b)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {
                "a": vector("i16", tuple(random.next() & MASK16 for _ in range(8))),
                "b": vector("i16", tuple(random.next() & MASK16 for _ in range(8))),
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
    values = [_signed(str(bits), 16) for bits in [*a, *b]]
    lanes = [f"0x{max(0, min(255, value)):02x}" for value in values]
    return {"return": {"element": "u8", "lanes": lanes}}
