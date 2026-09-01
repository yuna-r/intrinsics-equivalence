"""Development generator and executable model for _mm_unpackhi_epi64."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpackhi.i64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1), (2, 3)),
        ((0, 0xFFFFFFFFFFFFFFFF), (0xFFFFFFFFFFFFFFFF, 0)),
        ((0x8000000000000000, 0x7FFFFFFFFFFFFFFF), (0x7FFFFFFFFFFFFFFF, 0x8000000000000000)),
        ((0xAAAAAAAAAAAAAAAA, 0x5555555555555555), (0x0123456789ABCDEF, 0xFEDCBA9876543210)),
        ((1, 0xFFFFFFFFFFFFFFFE), (0xFFFFFFFFFFFFFFFF, 2)),
        ((0x00000000FFFFFFFF, 0xFFFFFFFF00000000), (0xFFFF0000FFFF0000, 0x0000FFFF0000FFFF)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "structured"},
            "operands": {"a": vector("i64", a), "b": vector("i64", b)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {
                "a": vector("i64", (random.next(), random.next())),
                "b": vector("i64", (random.next(), random.next())),
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    a = left["lanes"]
    b = right["lanes"]
    assert isinstance(a, list) and isinstance(b, list)
    return {"return": {"element": "i64", "lanes": [str(a[1]), str(b[1])]}}
