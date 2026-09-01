"""Development generator and executable model for _mm_and_si128."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.and.i32x4.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0xFFFFFFFF, 0x0F0F0F0F, 0xAAAAAAAA, 0x80000000),
         (0x12345678, 0xF0F0F0F0, 0x55555555, 0xFFFFFFFF)),
        ((0, 0, 0, 0), (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)),
        ((0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF),
         (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)),
        ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
         (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC)),
        ((1, 2, 4, 8), (1, 3, 7, 15)),
        ((0x80000000, 0x7FFFFFFF, 0x0000FFFF, 0xFFFF0000),
         (0xFFFFFFFF, 0x80000000, 0xFFFF0000, 0x0000FFFF)),
        ((0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
         (0x11111111, 0x22222222, 0x44444444, 0x88888888)),
        ((0xDEADBEEF, 0xCAFEBABE, 0x0BADF00D, 0xC001D00D),
         (0x00FF00FF, 0xFF00FF00, 0x33333333, 0x55555555)),
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
                "a": vector("i32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))),
                "b": vector("i32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))),
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
        f"0x{int(str(a), 16) & int(str(b), 16):08x}"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "i32", "lanes": lanes}}
