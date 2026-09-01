"""Development generator and executable model for _mm_slli_si128."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.slli-bytes.u8x16.imm8"
MINIMUM_COUNTS = {"standard": 6}
MASK = 0xFF
PATTERNS = (
    tuple(range(16)),
    tuple(range(16)),
    tuple(range(16)),
    tuple(range(16)),
    tuple(range(16)),
    (0xAA, 0x55, 0xCC, 0x33) * 4,
)


def _allowed(case: CaseDefinition) -> list[int]:
    definitions = case.data["immediates"]; assert isinstance(definitions, dict)
    item = definitions["imm8"]; assert isinstance(item, dict)
    values = item["values"]; assert isinstance(values, list)
    return [int(value) for value in values]


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case); allowed = _allowed(case)
    for index, (count, pattern) in enumerate(zip(allowed, PATTERNS, strict=True)):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "boundary"}, "immediates": {"imm8": count}, "operands": {"a": vector("u8", pattern)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "immediates": {"imm8": allowed[random.next() % len(allowed)]}, "operands": {"a": vector("u8", tuple(random.next() & MASK for _ in range(16)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands, immediates = record["operands"], record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    source = operands["a"]; assert isinstance(source, dict)
    lanes = source["lanes"]; assert isinstance(lanes, list)
    count = int(immediates["imm8"])
    values = (["0x00"] * count + [str(lane) for lane in lanes[:16 - count]]) if count < 16 else ["0x00"] * 16
    return {"return": {"element": "u8", "lanes": values}}
