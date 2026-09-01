"""Development generator and executable model for _mm_shuffle_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.shuffle.i32x4.imm8"
MINIMUM_COUNTS = {"standard": 16}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    definitions = case.data["immediates"]
    assert isinstance(definitions, dict)
    definition = definitions["imm8"]
    assert isinstance(definition, dict)
    allowed = definition["values"]
    assert isinstance(allowed, list)
    patterns = (
        (0, 1, 2, 3),
        (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
        (0xFFFFFFFF, 0, 0x80000000, 0x7FFFFFFF),
        (0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
    )
    for immediate in allowed:
        for pattern in patterns:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[0]},
                "generation": {"class": "structured"},
                "immediates": {"imm8": int(immediate)},
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
            "immediates": {"imm8": int(allowed[random.next() % len(allowed)])},
            "operands": {
                "a": vector(
                    "i32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))
                )
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
    control = int(immediates["imm8"])
    lanes = [str(source_lanes[(control >> (2 * lane)) & 3]) for lane in range(4)]
    return {"return": {"element": "i32", "lanes": lanes}}
