"""Development generator and executable model for _mm_slli_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.slli.i16x8.imm8"
MINIMUM_COUNTS = {"standard": 6}
MASK = 0xFFFF
PATTERNS = (
    (0, 1, 0x8000, 0xFFFF, 0x7FFF, 2, 0xAAAA, 0x5555),
    (1, 2, 4, 8, 0x8000, 0xFFFF, 0x7FFF, 0),
    (0x0001, 0x0002, 0x0101, 0x8080, 0xFFFF, 0x7FFF, 0x8000, 0),
    (0, 1, 2, 3, 0x8000, 0xFFFF, 0x7FFF, 0xAAAA),
    (0, 1, 0x8000, 0xFFFF, 0x7FFF, 2, 0xAAAA, 0x5555),
    (0x0123, 0x4567, 0x89AB, 0xCDEF, 0x1357, 0x2468, 0xBEEF, 0xDEAD),
)


def _allowed(case: CaseDefinition) -> list[int]:
    definitions = case.data["immediates"]; assert isinstance(definitions, dict)
    item = definitions["imm8"]; assert isinstance(item, dict)
    values = item["values"]; assert isinstance(values, list)
    return [int(value) for value in values]


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case); allowed = _allowed(case)
    for index, (count, pattern) in enumerate(zip(allowed, PATTERNS, strict=True)):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "boundary"}, "immediates": {"imm8": count}, "operands": {"a": vector("i16", pattern)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "immediates": {"imm8": allowed[random.next() % len(allowed)]}, "operands": {"a": vector("i16", tuple(random.next() & MASK for _ in range(8)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands, immediates = record["operands"], record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    source = operands["a"]; assert isinstance(source, dict)
    lanes = source["lanes"]; assert isinstance(lanes, list)
    count = int(immediates["imm8"])
    return {"return": vector("i16", tuple(((int(str(lane), 16) << count) & MASK) if count < 16 else 0 for lane in lanes))}
