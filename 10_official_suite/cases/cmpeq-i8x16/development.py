"""Development generator and executable model for _mm_cmpeq_epi8."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes


CASE_ID = "sse2.cmpeq.i8x16.default"
MINIMUM_COUNTS = {"standard": 8}
MASK8 = 0xFF


def _vector(values: tuple[int, ...]) -> dict[str, JSONValue]:
    return {
        "element": "i8",
        "lanes": [f"0x{value & MASK8:02x}" for value in values],
    }


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x00,) * 16, (0x00,) * 16),
        ((0x7F, 0x80, 0xFF, 0x01) * 4, (0x7F, 0x80, 0xFF, 0x01) * 4),
        ((0x00, 0x7F, 0x80, 0xFF) * 4, (0x01, 0x80, 0x7F, 0x00) * 4),
        (tuple(range(16)), tuple(reversed(range(16)))),
        ((0xAA, 0x55, 0xCC, 0x33) * 4, (0xAA, 0xAA, 0xCC, 0xCC) * 4),
        ((0x12, 0x34, 0x56, 0x78) * 4, (0x12, 0x35, 0x56, 0x79) * 4),
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
        a = tuple(random.next() & MASK8 for _ in range(16))
        random_b = tuple(random.next() & MASK8 for _ in range(16))
        b = tuple(a[index] if index % 4 == 0 else random_b[index] for index in range(16))
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
        "0xff" if int(str(a), 16) == int(str(b), 16) else "0x00"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "i8", "lanes": lanes}}
