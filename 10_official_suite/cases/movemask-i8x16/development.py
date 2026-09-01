"""Development generator and executable model for _mm_movemask_epi8."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar, vector


CASE_ID = "sse2.movemask.i8x16.default"
MINIMUM_COUNTS = {"standard": 8}
MASK8 = 0xFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0,) * 16,
        (0x80,) * 16,
        tuple(0x80 if lane % 2 else 0 for lane in range(16)),
        tuple(0 if lane % 2 else 0x80 for lane in range(16)),
        tuple(1 << (lane % 8) for lane in range(16)),
        tuple(0xFF if lane in {0, 7, 8, 15} else 0x7F for lane in range(16)),
        tuple(range(0x78, 0x88)),
        (0xAA, 0x55) * 8,
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"a": vector("i8", values)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {"a": vector("i8", tuple(random.next() & MASK8 for _ in range(16)))},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    mask = sum(((int(str(bits), 16) >> 7) & 1) << lane for lane, bits in enumerate(lanes))
    return {"return": scalar("i32", mask)}
