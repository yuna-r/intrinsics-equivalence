"""Development generator and executable model for _mm_cmpgt_pd."""

from __future__ import annotations

import struct
from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cmpgt.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}
TRUE_MASK = "0xffffffffffffffff"
FALSE_MASK = "0x0000000000000000"
EXPONENT_MASK = 0x7FF0000000000000
FRACTION_MASK = 0x000FFFFFFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3FF0000000000000, 0xC004000000000000),
         (0x3FF0000000000000, 0x4008000000000000), "structured"),
        ((0x0000000000000000, 0x8000000000000000),
         (0x8000000000000000, 0x0000000000000000), "boundary"),
        ((0x7FF0000000000000, 0xFFF0000000000000),
         (0x7FEFFFFFFFFFFFFF, 0x7FF0000000000000), "boundary"),
        ((0x0000000000000001, 0x8000000000000001),
         (0x0000000000000000, 0x8010000000000000), "boundary"),
        ((0x7FF8000000000042, 0x3FF0000000000000),
         (0x3FF0000000000000, 0xFFF8000000000043), "boundary"),
        ((0x7FF0000000000001, 0xBFF0000000000000),
         (0xBFF0000000000000, 0xFFF0000000000001), "boundary"),
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
                "a": vector("f64", (random.next(), random.next())),
                "b": vector("f64", (random.next(), random.next())),
            },
        }


def _is_nan(bits: int) -> bool:
    return bits & EXPONENT_MASK == EXPONENT_MASK and bool(bits & FRACTION_MASK)


def _as_float(bits: int) -> float:
    return struct.unpack(">d", bits.to_bytes(8, "big"))[0]


def _matches(a: int, b: int) -> bool:
    return not (_is_nan(a) or _is_nan(b)) and _as_float(a) > _as_float(b)


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
        TRUE_MASK if _matches(int(str(a), 16), int(str(b), 16)) else FALSE_MASK
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "f64", "lanes": lanes}}
