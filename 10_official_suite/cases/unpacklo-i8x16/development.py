"""Development generator and executable model for _mm_unpacklo_epi8."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpacklo.i8x16.default"
MINIMUM_COUNTS = {"standard": 4}
MASK = 0xFF
STRUCTURED = (
    (tuple(range(16)), tuple(range(0x10, 0x20))),
    ((0,) * 16, (0xFF,) * 16),
    ((0x7F, 0x80, 0xFF, 1) * 4, (1, 0xFF, 0x80, 0x7F) * 4),
    ((0xAA, 0x55, 0xCC, 0x33) * 4, (0x55, 0xAA, 0x33, 0xCC) * 4),
)


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case)
    for index, (a, b) in enumerate(STRUCTURED):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "structured"}, "operands": {"a": vector("i8", a), "b": vector("i8", b)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "operands": {"a": vector("i8", tuple(random.next() & MASK for _ in range(16))), "b": vector("i8", tuple(random.next() & MASK for _ in range(16)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]; assert isinstance(operands, dict)
    a, b = operands["a"], operands["b"]; assert isinstance(a, dict) and isinstance(b, dict)
    left, right = a["lanes"], b["lanes"]; assert isinstance(left, list) and isinstance(right, list)
    values = tuple(value for index in range(8) for value in (int(str(left[index]), 16), int(str(right[index]), 16)))
    return {"return": vector("i8", values)}
