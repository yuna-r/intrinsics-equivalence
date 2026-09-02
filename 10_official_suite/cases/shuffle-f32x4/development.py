"""Development generator and executable model for _mm_shuffle_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.shuffle.f32x4.imm8"
MINIMUM_COUNTS = {"standard": 12}


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
        (
            (0x00000000, 0x80000000, 0x7F800000, 0xFF800000),
            (0x7FC00042, 0xFFC00043, 0x7F800001, 0xFF800002),
        ),
        (
            (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
            (0x13579BDF, 0x2468ACE0, 0xAAAAAAAA, 0x55555555),
        ),
    )
    for immediate in allowed:
        for a, b in patterns:
            yield {
                "environment": {"fp_mode": "ieee", "rounding": modes[0]},
                "generation": {"class": "structured"},
                "immediates": {"imm8": int(immediate)},
                "operands": {"a": vector("f32", a), "b": vector("f32", b)},
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
            "immediates": {"imm8": int(allowed[random.next() % len(allowed)])},
            "operands": {
                "a": vector(
                    "f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))
                ),
                "b": vector(
                    "f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))
                ),
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
    lanes = (
        int(str(a[control & 3]), 16),
        int(str(a[(control >> 2) & 3]), 16),
        int(str(b[(control >> 4) & 3]), 16),
        int(str(b[(control >> 6) & 3]), 16),
    )
    return {"return": vector("f32", lanes)}
