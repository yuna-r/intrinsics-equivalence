"""Development generator and executable model for _mm_subs_epu16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.subs.u16x8.default"
MINIMUM_COUNTS = {"standard": 8}
MASK16 = 0xFFFF


def _vector(values: tuple[int, ...]) -> dict[str, JSONValue]:
    return {
        "element": "u16",
        "lanes": [f"0x{value & MASK16:04x}" for value in values],
    }


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 0xFFFF, 0xFFFE, 0x8000, 0x7FFF, 0x4000, 0xC000),
         (0, 1, 1, 0xFFFF, 0x8001, 0x7FFE, 0xC000, 0x4000)),
        ((0,) * 8, (0, 1, 0xFFFF, 0x8000, 0x7FFF, 2, 0x4000, 0xC000)),
        ((0xFFFF,) * 8, (0, 1, 0xFFFF, 0x8000, 0x7FFF, 2, 0x4000, 0xC000)),
        ((1, 2, 0x7FFF, 0x8000, 0xFFFE, 0xFFFF, 0x4000, 0xC000),
         (2, 1, 0x8000, 0x7FFF, 0xFFFF, 0xFFFE, 0xC000, 0x4000)),
        ((1, 0xFFFF, 0x7FFF, 0x8000, 0x1234, 0xEDCB, 0xAAAA, 0x5555),
         (0xFFFF, 1, 0x8000, 0x7FFF, 0xEDCB, 0x1234, 0x5555, 0xAAAA)),
        ((0x6000, 0xA000, 0x5000, 0xB000, 0x2000, 0xE000, 0x1000, 0xF000),
         (0x2000, 0x6000, 0xB000, 0x5000, 0xE000, 0x2000, 0xF000, 0x1000)),
        ((0xAAAA, 0x5555, 0xCCCC, 0x3333, 0xF0F0, 0x0F0F, 0x7FFE, 0x8001),
         (0x5555, 0xAAAA, 0x3333, 0xCCCC, 0x0F0F, 0xF0F0, 0x8001, 0x7FFE)),
        ((0x0123, 0x4567, 0x89AB, 0xCDEF, 0x1357, 0x2468, 0xBEEF, 0xDEAD),
         (0xFEDC, 0xBA98, 0x7654, 0x3210, 0xECA8, 0xDB97, 0x4111, 0x2153)),
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
        max(0, (int(str(a), 16) & MASK16) - (int(str(b), 16) & MASK16))
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {
        "return": {
            "element": "u16",
            "lanes": [f"0x{value:04x}" for value in values],
        }
    }
