"""Development generator and executable model for _mm_adds_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.adds.i16x8.default"
MINIMUM_COUNTS = {"standard": 8}
MASK16 = 0xFFFF
SIGNED_MIN = -0x8000
SIGNED_MAX = 0x7FFF


def _vector(values: tuple[int, ...]) -> dict[str, JSONValue]:
    return {
        "element": "i16",
        "lanes": [f"0x{value & MASK16:04x}" for value in values],
    }


def _signed16(value: str) -> int:
    unsigned = int(value, 16) & MASK16
    return unsigned if unsigned < 0x8000 else unsigned - 0x10000


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x7FFF, 0x7FFE, 0x8000, 0x8001, 0, 0xFFFF, 0x4000, 0xC000),
         (1, 2, 0xFFFF, 0xFFFE, 0, 1, 0x4000, 0xC000)),
        ((0x7FFF,) * 8, (0, 1, 0x7FFF, 0x8000, 0xFFFF, 2, 0x4000, 0xC000)),
        ((0x8000,) * 8, (0, 0xFFFF, 0x8000, 0x7FFF, 1, 0xFFFE, 0x4000, 0xC000)),
        ((0x7FFE, 0x7FFD, 0x8001, 0x8002, 0x3FFF, 0xC001, 1, 0xFFFF),
         (1, 2, 0xFFFF, 0xFFFE, 0x4000, 0xC000, 0x7FFE, 0x8001)),
        ((0, 1, 0xFFFF, 0x7FFF, 0x8000, 0x4000, 0xC000, 0x1234),
         (0, 0xFFFF, 1, 0xFFFF, 1, 0x3FFF, 0xC001, 0xEDCC)),
        ((0x6000, 0xA000, 0x5000, 0xB000, 0x2000, 0xE000, 0x1000, 0xF000),
         (0x2000, 0xE000, 0x4000, 0xC000, 0x6000, 0xA000, 0xF000, 0x1000)),
        ((0xAAAA, 0x5555, 0xCCCC, 0x3333, 0xF0F0, 0x0F0F, 0x7000, 0x9000),
         (0xAAAA, 0x5555, 0xCCCC, 0x3333, 0x0F0F, 0xF0F0, 0x1000, 0xF000)),
        ((0x0123, 0x4567, 0x89AB, 0xCDEF, 0x1357, 0x2468, 0xBEEF, 0xDEAD),
         (0x3210, 0x4567, 0xF000, 0xCDEF, 0x2468, 0x1357, 0xBEEF, 0xDEAD)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"a": _vector(a), "b": _vector(b)},
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
                "a": _vector(tuple(random.next() & MASK16 for _ in range(8))),
                "b": _vector(tuple(random.next() & MASK16 for _ in range(8))),
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
    values = [
        min(SIGNED_MAX, max(SIGNED_MIN, _signed16(str(a)) + _signed16(str(b))))
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {
        "return": {
            "element": "i16",
            "lanes": [f"0x{value & MASK16:04x}" for value in values],
        }
    }
