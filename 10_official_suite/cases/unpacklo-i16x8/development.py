"""Development generator and executable model for _mm_unpacklo_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpacklo.i16x8.default"
MINIMUM_COUNTS = {"standard": 4}
MASK = 0xFFFF
STRUCTURED = (
    (tuple(range(8)), tuple(range(0x10, 0x18))),
    ((0,) * 8, (0xFFFF,) * 8),
    ((0x7FFF, 0x8000, 0xFFFF, 1) * 2, (1, 0xFFFF, 0x8000, 0x7FFF) * 2),
    ((0xAAAA, 0x5555, 0xCCCC, 0x3333) * 2, (0x5555, 0xAAAA, 0x3333, 0xCCCC) * 2),
)


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case)
    for index, (a, b) in enumerate(STRUCTURED):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "structured"}, "operands": {"a": vector("i16", a), "b": vector("i16", b)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "operands": {"a": vector("i16", tuple(random.next() & MASK for _ in range(8))), "b": vector("i16", tuple(random.next() & MASK for _ in range(8)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]; assert isinstance(operands, dict)
    a, b = operands["a"], operands["b"]; assert isinstance(a, dict) and isinstance(b, dict)
    left, right = a["lanes"], b["lanes"]; assert isinstance(left, list) and isinstance(right, list)
    values = tuple(value for index in range(4) for value in (int(str(left[index]), 16), int(str(right[index]), 16)))
    return {"return": vector("i16", values)}
