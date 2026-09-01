"""Development generator and executable model for _mm_movemask_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar, vector


CASE_ID = "sse2.movemask.f64x2.default"
MINIMUM_COUNTS = {"standard": 8}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 0),
        (0x8000000000000000, 0),
        (0, 0x8000000000000000),
        (0x8000000000000000, 0x8000000000000000),
        (0x7FF0000000000000, 0xFFF0000000000000),
        (0x7FF8000000000042, 0xFFF8000000000042),
        (0x3FF0000000000000, 0xBFF0000000000000),
        (0xFFFFFFFFFFFFFFFF, 0x7FFFFFFFFFFFFFFF),
    )
    for index, values in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"a": vector("f64", values)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {"a": vector("f64", (random.next(), random.next()))},
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    source = operands["a"]
    assert isinstance(source, dict)
    lanes = source["lanes"]
    assert isinstance(lanes, list)
    mask = sum(((int(str(bits), 16) >> 63) & 1) << lane for lane, bits in enumerate(lanes))
    return {"return": scalar("i32", mask)}
