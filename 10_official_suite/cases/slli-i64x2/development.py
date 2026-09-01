"""Development generator and executable model for _mm_slli_epi64."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.slli.i64x2.imm8"
MINIMUM_COUNTS = {"standard": 6}
MASK = 0xFFFFFFFFFFFFFFFF
PATTERNS = (
    (0, 0xFFFFFFFFFFFFFFFF),
    (1, 0x8000000000000000),
    (0x0000000100000001, 0xFFFFFFFF00000001),
    (1, 0x8000000000000001),
    (0x7FFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF),
    (0x0123456789ABCDEF, 0xFEDCBA9876543210),
)


def _allowed(case: CaseDefinition) -> list[int]:
    definitions = case.data["immediates"]; assert isinstance(definitions, dict)
    item = definitions["imm8"]; assert isinstance(item, dict)
    values = item["values"]; assert isinstance(values, list)
    return [int(value) for value in values]


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case); allowed = _allowed(case)
    for index, (count, pattern) in enumerate(zip(allowed, PATTERNS, strict=True)):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "boundary"}, "immediates": {"imm8": count}, "operands": {"a": vector("i64", pattern)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "immediates": {"imm8": allowed[random.next() % len(allowed)]}, "operands": {"a": vector("i64", (random.next(), random.next()))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands, immediates = record["operands"], record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    source = operands["a"]; assert isinstance(source, dict)
    lanes = source["lanes"]; assert isinstance(lanes, list)
    count = int(immediates["imm8"])
    return {"return": vector("i64", tuple(((int(str(lane), 16) << count) & MASK) if count < 64 else 0 for lane in lanes))}
