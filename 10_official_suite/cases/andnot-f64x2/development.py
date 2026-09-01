"""Development generator and executable model for _mm_andnot_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.andnot.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}
MASK64 = 0xFFFFFFFFFFFFFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 0), (0xFFFFFFFFFFFFFFFF, 0x8000000000000000)),
        ((0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF), (0, 0xFFFFFFFFFFFFFFFF)),
        ((0xAAAAAAAAAAAAAAAA, 0x5555555555555555), (0x5555555555555555, 0xAAAAAAAAAAAAAAAA)),
        ((0x7FF0000000000000, 0x8000000000000000), (0x7FF8000000000042, 0xFFFFFFFFFFFFFFFF)),
        ((0x0123456789ABCDEF, 0xFEDCBA9876543210), (0x1111111111111111, 0xEEEEEEEEEEEEEEEE)),
        ((1, 2), (0xFFFFFFFFFFFFFFFF, 0xFFFFFFFFFFFFFFFF)),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "structured"},
            "operands": {"a": vector("f64", a), "b": vector("f64", b)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
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
    a = left["lanes"]
    b = right["lanes"]
    assert isinstance(a, list) and isinstance(b, list)
    lanes = [
        f"0x{((~int(str(x), 16)) & int(str(y), 16)) & MASK64:016x}"
        for x, y in zip(a, b, strict=True)
    ]
    return {"return": {"element": "f64", "lanes": lanes}}
