"""Development generator and executable model for _mm_xor_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.xor.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0xFFFFFFFFFFFFFFFF, 0x0000000000000000),
         (0x0123456789ABCDEF, 0xFEDCBA9876543210)),
        ((0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
         (0x5555555555555555, 0xAAAAAAAAAAAAAAAA)),
        ((0x7FF8000000000042, 0xFFF0000000000000),
         (0x0000000000000042, 0x8000000000000000)),
        ((0x8000000000000000, 0x0000000000000001),
         (0x8000000000000000, 0x8000000000000001)),
        ((0xFFFF0000FFFF0000, 0x00FF00FF00FF00FF),
         (0x0F0F0F0F0F0F0F0F, 0xF0F0F0F0F0F0F0F0)),
        ((0x7FEFFFFFFFFFFFFF, 0x0010000000000000),
         (0xFFEFFFFFFFFFFFFF, 0x8010000000000000)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "structured"},
            "operands": {"a": vector("f64", a), "b": vector("f64", b)},
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
                "a": vector("f64", (random.next(), random.next())),
                "b": vector("f64", (random.next(), random.next())),
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
        f"0x{int(str(a), 16) ^ int(str(b), 16):016x}"
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "f64", "lanes": lanes}}
