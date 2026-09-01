"""Development generator and executable model for _mm_mullo_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.mullo.i16x8.default"
MINIMUM_COUNTS = {"standard": 4}
MASK = 0xFFFF
STRUCTURED = (
    ((0, 1, 0xFFFF, 0x7FFF, 0x8000, 2, 0xFFFE, 0x4000), (0, 1, 2, 2, 2, 0xFFFF, 0x8000, 4)),
    ((0x7FFF,) * 8, (0x7FFF, 0x8000, 1, 2, 3, 4, 0xFFFF, 0)),
    ((0x8000,) * 8, (0x8000, 0x7FFF, 1, 2, 3, 4, 0xFFFF, 0)),
    ((0xAAAA, 0x5555, 0x1234, 0xFEDC, 0x0101, 0x1010, 0xFFFF, 2), (0x5555, 0xAAAA, 0xFEDC, 0x1234, 0x1010, 0x0101, 2, 0xFFFF)),
)


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case)
    for index, (a, b) in enumerate(STRUCTURED):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "boundary"}, "operands": {"a": vector("i16", a), "b": vector("i16", b)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "operands": {"a": vector("i16", tuple(random.next() & MASK for _ in range(8))), "b": vector("i16", tuple(random.next() & MASK for _ in range(8)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]; assert isinstance(operands, dict)
    a, b = operands["a"], operands["b"]; assert isinstance(a, dict) and isinstance(b, dict)
    left, right = a["lanes"], b["lanes"]; assert isinstance(left, list) and isinstance(right, list)
    return {"return": vector("i16", tuple((int(str(x), 16) * int(str(y), 16)) & MASK for x, y in zip(left, right, strict=True)))}
