"""Development generator and executable model for _mm_cmpgt_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cmpgt.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (
            (0, 1, 0xFFFFFFFF, 0x7FFFFFFF),
            (0, 0, 0, 0x80000000),
            "structured",
        ),
        (
            (0x80000000, 0x7FFFFFFF, 0xFFFFFFFF, 0),
            (0x7FFFFFFF, 0x80000000, 0, 0xFFFFFFFF),
            "boundary",
        ),
        (
            (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
            (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
            "boundary",
        ),
        (
            (1, 0xFFFFFFFE, 0x40000000, 0xC0000000),
            (0xFFFFFFFF, 0xFFFFFFFF, 0x3FFFFFFF, 0xBFFFFFFF),
            "boundary",
        ),
        (
            (0x80000001, 0xFFFFFFFE, 1, 0x7FFFFFFE),
            (0x80000000, 0xFFFFFFFF, 2, 0x7FFFFFFF),
            "boundary",
        ),
        (
            (0xAAAAAAAA, 0x55555555, 0xDEADBEEF, 0x01234567),
            (0x55555555, 0xAAAAAAAA, 0xCAFEBABE, 0x89ABCDEF),
            "structured",
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


def _signed32(value: str) -> int:
    unsigned = int(value, 16) & MASK32
    return unsigned if unsigned < 0x80000000 else unsigned - 0x100000000


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
        "0xffffffff" if _signed32(str(a)) > _signed32(str(b)) else "0x00000000"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "i32", "lanes": lanes}}
