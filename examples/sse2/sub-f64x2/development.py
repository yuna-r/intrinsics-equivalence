"""Development generator and executable model for _mm_sub_pd."""

from __future__ import annotations

import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import (
    SplitMix64,
    random_finite_f64_bits,
    rounding_modes,
    vector,
)


CASE_ID = "sse2.sub.f64x2.default"
MINIMUM_COUNTS = {"standard": 10}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x4024000000000000, 0xC010000000000000),
         (0x4008000000000000, 0x4000000000000000), "structured"),
        ((0, 0x8000000000000000), (0, 0), "boundary"),
        ((0x3FF0000000000000, 0xBFF0000000000000),
         (0x3FF0000000000000, 0xBFF0000000000000), "boundary"),
        ((0x0000000000000001, 0x8000000000000001),
         (0, 0x8000000000000000), "boundary"),
        ((0x0010000000000000, 0x8010000000000000),
         (0x000FFFFFFFFFFFFF, 0x800FFFFFFFFFFFFF), "boundary"),
        ((0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF),
         (0xBFF0000000000000, 0x3FF0000000000000), "boundary"),
        ((0x7FF0000000000000, 0xFFF0000000000000),
         (0x3FF0000000000000, 0xBFF0000000000000), "boundary"),
        ((0x7FF8000000000001, 0x7FF0000000000001),
         (0x3FF0000000000000, 0x3FF0000000000000), "boundary"),
        ((0x3FF0000000000000, 0xBFF0000000000000),
         (0x3CA0000000000000, 0xBCA0000000000000), "boundary"),
        ((0x8000000000000001, 0x800FFFFFFFFFFFFF),
         (0x0000000000000001, 0x000FFFFFFFFFFFFF), "boundary"),
    )
    for index, (a, b, generation_class) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": generation_class},
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
                "a": vector(
                    "f64",
                    (random_finite_f64_bits(random), random_finite_f64_bits(random)),
                ),
                "b": vector(
                    "f64",
                    (random_finite_f64_bits(random), random_finite_f64_bits(random)),
                ),
            },
        }


def _from_bits(bits: str) -> float:
    return struct.unpack(">d", int(bits, 16).to_bytes(8, "big"))[0]


def _to_bits(value: float) -> str:
    integer = int.from_bytes(struct.pack(">d", value), "big")
    return f"0x{integer:016x}"


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
        _to_bits(_from_bits(str(a)) - _from_bits(str(b)))
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "f64", "lanes": lanes}}
