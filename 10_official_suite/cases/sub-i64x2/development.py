"""Development generator and executable model for _mm_sub_epi64."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.sub.i64x2.default"
MINIMUM_COUNTS = {"standard": 4}
MASK = 0xFFFFFFFFFFFFFFFF
STRUCTURED = (
    ((0, 0), (0, 0)),
    ((0x8000000000000000, 0x7FFFFFFFFFFFFFFF), (1, 0xFFFFFFFFFFFFFFFF)),
    ((0, 0xFFFFFFFFFFFFFFFF), (1, 0xFFFFFFFFFFFFFFFF)),
    ((0xAAAAAAAAAAAAAAAA, 0x0123456789ABCDEF), (0x5555555555555555, 0xFEDCBA9876543210)),
)


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    for index, (a, b) in enumerate(STRUCTURED):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]},
               "generation": {"class": "boundary"},
               "operands": {"a": vector("i64", a), "b": vector("i64", b)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]},
               "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text},
               "operands": {"a": vector("i64", (random.next(), random.next())),
                            "b": vector("i64", (random.next(), random.next()))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]
    assert isinstance(operands, dict)
    a, b = operands["a"], operands["b"]
    assert isinstance(a, dict) and isinstance(b, dict)
    left, right = a["lanes"], b["lanes"]
    assert isinstance(left, list) and isinstance(right, list)
    values = tuple((int(str(x), 16) - int(str(y), 16)) & MASK for x, y in zip(left, right, strict=True))
    return {"return": vector("i64", values)}
