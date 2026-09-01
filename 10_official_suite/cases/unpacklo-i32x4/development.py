"""Development generator and executable model for _mm_unpacklo_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.unpacklo.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 2, 3), (4, 5, 6, 7), "structured"),
        (
            (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
            (0xFFFFFFFF, 0, 0x7FFFFFFF, 0x80000000),
            "boundary",
        ),
        (
            (0x80000000, 0x7FFFFFFF, 0, 0xFFFFFFFF),
            (0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 0),
            "boundary",
        ),
        (
            (0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
            (0x11111111, 0x22222222, 0x44444444, 0x88888888),
            "structured",
        ),
        (
            (0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0xCAFEBABE),
            (0x76543210, 0xFEDCBA98, 0x0BADF00D, 0xC001D00D),
            "structured",
        ),
        (
            (1, 2, 0xFFFFFFFE, 0xFFFFFFFF),
            (0xFFFFFFFF, 0xFFFFFFFE, 2, 1),
            "boundary",
        ),
    )
    for index, (a, b, generation_class) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": generation_class},
            "operands": {"a": vector("i32", a), "b": vector("i32", b)},
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
                "a": vector("i32", tuple(random.next() & MASK32 for _ in range(4))),
                "b": vector("i32", tuple(random.next() & MASK32 for _ in range(4))),
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
    lanes = [
        str(left_lanes[0]),
        str(right_lanes[0]),
        str(left_lanes[1]),
        str(right_lanes[1]),
    ]
    return {"return": {"element": "i32", "lanes": lanes}}
