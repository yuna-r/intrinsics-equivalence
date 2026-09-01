"""Development generator and executable model for _mm_unpackhi_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpackhi.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3FF0000000000000, 0x4000000000000000),
         (0x4008000000000000, 0x4010000000000000)),
        ((0x0000000000000000, 0x8000000000000000),
         (0x8000000000000000, 0x0000000000000000)),
        ((0x7FF8000000000042, 0x7FF0000000000001),
         (0xFFF8000000001234, 0xFFF0000000000000)),
        ((0x0000000000000001, 0x000FFFFFFFFFFFFF),
         (0x8000000000000001, 0x800FFFFFFFFFFFFF)),
        ((0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
         (0x0123456789ABCDEF, 0xFEDCBA9876543210)),
        ((0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF),
         (0x0010000000000000, 0x8010000000000000)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "structured"},
            "operands": {"a": vector("f64", a), "b": vector("f64", b)},
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
            "operands": {
                "a": vector("f64", (random.next(), random.next())),
                "b": vector("f64", (random.next(), random.next())),
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    left_lanes = left["lanes"]
    right_lanes = right["lanes"]
    assert isinstance(left_lanes, list) and isinstance(right_lanes, list)
    return {
        "return": {
            "element": "f64",
            "lanes": [str(left_lanes[1]), str(right_lanes[1])],
        }
    }
