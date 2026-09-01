"""Development generator and executable model for _mm_cmpeq_epi16."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.cmpeq.i16x8.default"
MINIMUM_COUNTS = {"standard": 8}
MASK16 = 0xFFFF


def _vector(values: tuple[int, ...]) -> dict[str, JSONValue]:
    return {
        "element": "i16",
        "lanes": [f"0x{value & MASK16:04x}" for value in values],
    }


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 0xFFFF, 0x7FFF, 0x8000, 2, 0xFFFE, 0x5555),
         (0, 1, 0xFFFF, 0x7FFF, 0x8000, 2, 0xFFFE, 0x5555)),
        ((0, 1, 0xFFFF, 0x7FFF, 0x8000, 2, 0xFFFE, 0x5555),
         (1, 0, 0xFFFE, 0x8000, 0x7FFF, 3, 0xFFFF, 0xAAAA)),
        ((0x7FFF,) * 8, (0x7FFF, 0x8000, 0x7FFF, 0xFFFF, 0x7FFF, 0, 0x7FFF, 1)),
        ((0x8000,) * 8, (0x8000, 0x7FFF, 0x8000, 0xFFFF, 0x8000, 0, 0x8000, 1)),
        ((0, 0xFFFF, 0x7FFF, 0x8000, 1, 0xFFFE, 0x4000, 0xC000),
         (0, 0, 0x7FFF, 0x7FFF, 1, 0xFFFF, 0x4000, 0x4000)),
        ((0xAAAA, 0x5555, 0xCCCC, 0x3333, 0xF0F0, 0x0F0F, 0x1234, 0xEDCB),
         (0xAAAA, 0xAAAA, 0xCCCC, 0xCCCC, 0xF0F0, 0xF0F0, 0x1234, 0x1234)),
        ((0x7FFE, 0x8001, 0x3FFF, 0xC001, 0x0100, 0xFF00, 0x0001, 0xFFFF),
         (0x7FFE, 0x8002, 0x3FFF, 0xC002, 0x0100, 0xFF01, 0x0001, 0)),
        ((0x0123, 0x4567, 0x89AB, 0xCDEF, 0x1357, 0x2468, 0xBEEF, 0xDEAD),
         (0x0123, 0x4566, 0x89AB, 0xCDEE, 0x1357, 0x2467, 0xBEEF, 0xDEAC)),
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
        a = tuple(random.next() & MASK16 for _ in range(8))
        fresh = tuple(random.next() & MASK16 for _ in range(8))
        b = tuple(a[index] if index % 2 == 0 else fresh[index] for index in range(8))
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
            "operands": {"a": _vector(a), "b": _vector(b)},
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
        "0xffff" if int(str(a), 16) == int(str(b), 16) else "0x0000"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "i16", "lanes": lanes}}
