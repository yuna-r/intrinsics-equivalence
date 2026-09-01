"""Development generator and executable model for _mm_adds_epu8."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.adds.u8x16.default"
MINIMUM_COUNTS = {"standard": 8}
MASK8 = 0xFF


def _vector(values: tuple[int, ...]) -> dict[str, JSONValue]:
    return {
        "element": "u8",
        "lanes": [f"0x{value & MASK8:02x}" for value in values],
    }


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x00,) * 16, (0x00,) * 16),
        ((0xFF, 0xFE, 0x80, 0x7F) * 4, (0x01, 0x02, 0x80, 0x81) * 4),
        ((0x00, 0x01, 0x7E, 0x7F) * 4, (0xFF, 0xFE, 0x81, 0x80) * 4),
        (tuple(range(16)), tuple(reversed(range(16)))),
        ((0xF0, 0xE0, 0xD0, 0xC0) * 4, (0x10, 0x20, 0x30, 0x40) * 4),
        ((0xAA, 0x55, 0xCC, 0x33) * 4, (0x55, 0xAA, 0x33, 0xCC) * 4),
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
                "a": _vector(tuple(random.next() & MASK8 for _ in range(16))),
                "b": _vector(tuple(random.next() & MASK8 for _ in range(16))),
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
        f"0x{min(MASK8, int(str(a), 16) + int(str(b), 16)):02x}"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "u8", "lanes": lanes}}
