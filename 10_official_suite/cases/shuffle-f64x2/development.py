"""Development generator and executable model for _mm_shuffle_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.shuffle.f64x2.imm8"
MINIMUM_COUNTS = {"standard": 16}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    definitions = case.data["immediates"]
    assert isinstance(definitions, dict)
    definition = definitions["imm8"]
    assert isinstance(definition, dict)
    allowed = definition["values"]
    assert isinstance(allowed, list)
    patterns = (
        ((0x3FF0000000000000, 0x4000000000000000), (0x4008000000000000, 0x4010000000000000)),
        ((0, 0x8000000000000000), (0x7FF0000000000000, 0xFFF0000000000000)),
        ((0x7FF8000000000042, 0x7FF0000000000001), (0xFFF8000000001234, 0xFFF0000000000001)),
        ((0x0123456789ABCDEF, 0xFEDCBA9876543210), (0xAAAAAAAAAAAAAAAA, 0x5555555555555555)),
    )
    for immediate in allowed:
        for a, b in patterns:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[0]},
                "generation": {"class": "structured"},
                "immediates": {"imm8": int(immediate)},
                "operands": {"a": vector("f64", a), "b": vector("f64", b)},
            }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "immediates": {"imm8": int(allowed[random.next() % len(allowed)])},
            "operands": {
                "a": vector("f64", (random.next(), random.next())),
                "b": vector("f64", (random.next(), random.next())),
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    immediates = record["immediates"]
    assert isinstance(operands, dict) and isinstance(immediates, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    a = left["lanes"]
    b = right["lanes"]
    assert isinstance(a, list) and isinstance(b, list)
    control = int(immediates["imm8"])
    return {
        "return": {
            "element": "f64",
            "lanes": [str(a[control & 1]), str(b[(control >> 1) & 1])],
        }
    }
