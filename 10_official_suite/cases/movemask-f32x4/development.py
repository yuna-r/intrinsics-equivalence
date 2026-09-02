"""Development generator and executable model for _mm_movemask_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar, vector


CASE_ID = "sse2.movemask.f32x4.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 0, 0, 0),
        (0x80000000, 0, 0, 0),
        (0, 0x80000000, 0, 0),
        (0, 0, 0x80000000, 0),
        (0, 0, 0, 0x80000000),
        (0x7F800000, 0xFF800000, 0x7FC00042, 0xFFC00042),
        (0x3F800000, 0xBF800000, 0x00000001, 0x80000001),
        (0xFFFFFFFF, 0x7FFFFFFF, 0xAAAAAAAA, 0x55555555),
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"a": vector("f32", values)},
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
                "a": vector("f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4)))
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    mask = sum(
        ((int(str(bits), 16) >> 31) & 1) << lane
        for lane, bits in enumerate(lanes)
    )
    return {"return": scalar("i32", mask)}
