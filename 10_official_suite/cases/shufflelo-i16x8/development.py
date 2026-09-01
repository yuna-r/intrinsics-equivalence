"""Development generator and executable model for _mm_shufflelo_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.shufflelo.i16x8.imm8"
MINIMUM_COUNTS = {"standard": 20}
MASK16 = 0xFFFF


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
        tuple(range(8)),
        (0, 0xFFFF, 0x8000, 0x7FFF, 1, 2, 3, 4),
        (0xAAAA, 0x5555, 0xCCCC, 0x3333, 0x1111, 0x2222, 0x4444, 0x8888),
        (0x0123, 0x4567, 0x89AB, 0xCDEF, 0xFEDC, 0xBA98, 0x7654, 0x3210),
    )
    for immediate in allowed:
        for pattern in patterns:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[0]},
                "generation": {"class": "structured"},
                "immediates": {"imm8": int(immediate)},
                "operands": {"a": vector("i16", pattern)},
            }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "immediates": {"imm8": int(allowed[random.next() % len(allowed)])},
            "operands": {"a": vector("i16", tuple(random.next() & MASK16 for _ in range(8)))},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    immediates = record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    control = int(immediates["imm8"])
    result = [str(lanes[(control >> (2 * lane)) & 3]) for lane in range(4)]
    result.extend(str(lane) for lane in lanes[4:])
    return {"return": {"element": "i16", "lanes": result}}
