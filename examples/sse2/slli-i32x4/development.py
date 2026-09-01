"""Development generator and executable model for _mm_slli_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.slli.i32x4.imm8"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def _allowed_immediates(case: CaseDefinition) -> list[int]:
    definitions = case.data["immediates"]
    assert isinstance(definitions, dict)
    definition = definitions["imm8"]
    assert isinstance(definition, dict)
    values = definition["values"]
    assert isinstance(values, list)
    return [int(value) for value in values]


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    allowed = _allowed_immediates(case)
    patterns = (
        (0, 1, 0x80000000, 0xFFFFFFFF),
        (1, 0x7FFFFFFF, 0x80000000, 0xFFFFFFFF),
        (0x00010001, 0xFFFF0001, 0xAAAAAAAA, 0x55555555),
        (1, 2, 0x80000000, 0xFFFFFFFF),
        (0, 1, 0x7FFFFFFF, 0xFFFFFFFF),
        (0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0x80000001),
    )
    for index, (immediate, pattern) in enumerate(zip(allowed, patterns, strict=True)):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "immediates": {"imm8": immediate},
            "operands": {"a": vector("i32", pattern)},
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
            "immediates": {"imm8": allowed[random.next() % len(allowed)]},
            "operands": {
                "a": vector("i32", tuple(random.next() & MASK32 for _ in range(4)))
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    immediates = record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    source_lanes = source["lanes"]
    assert isinstance(source_lanes, list)
    count = int(immediates["imm8"])
    lanes = [
        f"0x{((int(str(lane), 16) << count) & MASK32) if count < 32 else 0:08x}"
        for lane in source_lanes
    ]
    return {"return": {"element": "i32", "lanes": lanes}}
