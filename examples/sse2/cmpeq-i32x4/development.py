"""Development generator and executable model for _mm_cmpeq_epi32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cmpeq.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}
MASK32 = 0xFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 0, 0, 0), (0, 0, 0, 0)),
        ((0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 1),
         (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 1)),
        ((0, 1, 0xFFFFFFFF, 0x80000000), (1, 0, 0x7FFFFFFF, 0x80000001)),
        ((0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
         (0, 0, 0x80000000, 0xFFFFFFFF)),
        ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
         (0xAAAAAAAA, 0xAAAAAAAA, 0xCCCCCCCC, 0xCCCCCCCC)),
        ((0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0x0BADF00D),
         (0x01234567, 0x89ABCDEE, 0xDEADBEEF, 0x0BADF00C)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "structured"},
            "operands": {"a": vector("i32", a), "b": vector("i32", b)},
        }
    while True:
        a = tuple(random.next() & MASK32 for _ in range(4))
        b_random = tuple(random.next() & MASK32 for _ in range(4))
        b = (a[0], b_random[1], a[2], b_random[3])
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
            "operands": {"a": vector("i32", a), "b": vector("i32", b)},
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
        "0xffffffff" if int(str(a), 16) == int(str(b), 16) else "0x00000000"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "i32", "lanes": lanes}}
