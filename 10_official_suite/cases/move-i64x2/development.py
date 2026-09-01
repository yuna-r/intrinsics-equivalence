"""Development generator and executable model for _mm_move_epi64."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.move.i64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 0),
        (1, 2),
        (0xFFFFFFFFFFFFFFFF, 0x8000000000000000),
        (0x8000000000000000, 0x7FFFFFFFFFFFFFFF),
        (0x0123456789ABCDEF, 0xFEDCBA9876543210),
        (0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
        (0x00000000FFFFFFFF, 0xFFFFFFFF00000000),
        (0x7FFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF),
    )
    for index, value in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"a": vector("i64", value)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {"a": vector("i64", (random.next(), random.next()))},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    return {
        "return": {
            "element": "i64",
            "lanes": [str(lanes[0]), "0x0000000000000000"],
        }
    }
