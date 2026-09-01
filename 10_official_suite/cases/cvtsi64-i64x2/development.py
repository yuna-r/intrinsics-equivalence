"""Development generator and executable model for _mm_cvtsi64_si128."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar


CASE_ID = "sse2.cvtsi64.i64x2.default"
I64_BOUNDARY = (
    0,
    1,
    0xFFFFFFFFFFFFFFFF,
    0x7FFFFFFFFFFFFFFF,
    0x8000000000000000,
    0x00000000FFFFFFFF,
    0xFFFFFFFF00000000,
    0xAAAAAAAAAAAAAAAA,
    0x5555555555555555,
    0x0123456789ABCDEF,
)
MINIMUM_COUNTS = {"standard": len(I64_BOUNDARY)}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    for index, value in enumerate(I64_BOUNDARY):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"value": scalar("i64", value)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {"value": scalar("i64", random.next())},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands["value"]
    assert isinstance(value, dict)
    return {
        "return": {
            "element": "i64",
            "lanes": [str(value["bits"]), "0x0000000000000000"],
        }
    }
