"""Development generator and executable model for _mm_unpackhi_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpackhi.i16x8.default"
MINIMUM_COUNTS = {"standard": 8}
MASK16 = 0xFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 2, 3, 4, 5, 6, 7), (8, 9, 10, 11, 12, 13, 14, 15)),
        ((0, 0xFFFF, 0x8000, 0x7FFF) * 2, (0xFFFF, 0, 0x7FFF, 0x8000) * 2),
        ((0xAAAA, 0x5555, 0xCCCC, 0x3333) * 2, (0x1111, 0x2222, 0x4444, 0x8888) * 2),
        ((1, 2, 3, 4, 0xFFFC, 0xFFFD, 0xFFFE, 0xFFFF), (0xFFFF, 0xFFFE, 0xFFFD, 0xFFFC, 4, 3, 2, 1)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "structured"},
            "operands": {"a": vector("i16", a), "b": vector("i16", b)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {
                "a": vector("i16", tuple(random.next() & MASK16 for _ in range(8))),
                "b": vector("i16", tuple(random.next() & MASK16 for _ in range(8))),
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
    lanes = [item for lane in range(4, 8) for item in (str(a[lane]), str(b[lane]))]
    return {"return": {"element": "i16", "lanes": lanes}}
