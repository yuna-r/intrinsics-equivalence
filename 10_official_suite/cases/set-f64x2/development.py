"""Development generator and executable model for _mm_set_pd."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, scalar


CASE_ID = "sse2.set.f64x2.high-low"
MINIMUM_COUNTS = {"standard": 10}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        (0, 0x8000000000000000),
        (0x3FF0000000000000, 0xBFF0000000000000),
        (0x7FF0000000000000, 0xFFF0000000000000),
        (0x7FF8000000000042, 0x7FF0000000000001),
        (0x0000000000000001, 0x8000000000000001),
        (0x000FFFFFFFFFFFFF, 0x800FFFFFFFFFFFFF),
        (0x0010000000000000, 0x8010000000000000),
        (0x7FEFFFFFFFFFFFFF, 0xFFEFFFFFFFFFFFFF),
        (0x0123456789ABCDEF, 0xFEDCBA9876543210),
        (0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
    )
    for index, (high, low) in enumerate(structured):
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
            "generation": {"class": "boundary"},
            "operands": {"high": scalar("f64", high), "low": scalar("f64", low)},
        }
    while True:
        yield {
            "environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
            "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
            "operands": {
                "high": scalar("f64", random.next()),
                "low": scalar("f64", random.next()),
            },
        }


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    high = operands["high"]
    low = operands["low"]
    assert isinstance(high, dict) and isinstance(low, dict)
    return {
        "return": {
            "element": "f64",
            "lanes": [str(low["bits"]), str(high["bits"])],
        }
    }
