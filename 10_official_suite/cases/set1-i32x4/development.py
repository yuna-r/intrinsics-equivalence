"""Development generator and executable model for _mm_set1_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar


CASE_ID = "sse2.set1.i32x4.default"
I32_BOUNDARY = (
    0,
    1,
    0xFFFFFFFF,
    0x7FFFFFFF,
    0x80000000,
    0x0000FFFF,
    0xFFFF0000,
    0xAAAAAAAA,
    0x55555555,
    0x01234567,
)
MINIMUM_COUNTS = {"standard": len(I32_BOUNDARY)}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    for index, value in enumerate(I32_BOUNDARY):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"value": scalar("i32", value)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {"value": scalar("i32", random.next())},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands["value"]
    assert isinstance(value, dict)
    bits = str(value["bits"])
    return {"return": {"element": "i32", "lanes": [bits] * 4}}
