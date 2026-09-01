"""Development generator and executable model for _mm_set1_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar


CASE_ID = "sse2.set1.f64x2.default"
F64_BOUNDARY = (
    0x0000000000000000,
    0x8000000000000000,
    0x0000000000000001,
    0x8000000000000001,
    0x000FFFFFFFFFFFFF,
    0x800FFFFFFFFFFFFF,
    0x0010000000000000,
    0x8010000000000000,
    0x7FEFFFFFFFFFFFFF,
    0xFFEFFFFFFFFFFFFF,
    0x7FF0000000000000,
    0xFFF0000000000000,
    0x7FF8000000000001,
    0x7FF0000000000001,
    0x3FF0000000000000,
    0xBFF0000000000000,
    0x4000000000000000,
    0x4024000000000000,
    0x4034000000000000,
    0x3FEFFFFFFFFFFFFF,
)
MINIMUM_COUNTS = {"standard": len(F64_BOUNDARY)}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    for index, value in enumerate(F64_BOUNDARY):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
            "operands": {"value": scalar("f64", value)},
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
            "operands": {"value": scalar("f64", random.next())},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    value = operands["value"]
    assert isinstance(value, dict)
    bits = str(value["bits"])
    return {"return": {"element": "f64", "lanes": [bits, bits]}}
