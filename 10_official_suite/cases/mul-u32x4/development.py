"""Development generator and executable model for _mm_mul_epu32."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.mul.u32x4.default"
MINIMUM_COUNTS = {"standard": 4}
MASK = 0xFFFFFFFF
STRUCTURED = (
    ((0, 1, 2, 3), (0, 4, 5, 6)),
    ((0xFFFFFFFF, 0, 0xFFFFFFFF, 0), (0xFFFFFFFF, 1, 2, 3)),
    ((0x80000000, 0xDEADBEEF, 0x7FFFFFFF, 0xCAFEBABE), (2, 1, 3, 4)),
    ((0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210), (0x76543210, 0xFEDCBA98, 0x89ABCDEF, 0x01234567)),
)


def candidates(case: CaseDefinition, *, seed_text: str) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16)); modes = rounding_modes(case)
    for index, (a, b) in enumerate(STRUCTURED):
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[index % len(modes)]}, "generation": {"class": "boundary"}, "operands": {"a": vector("u32", a), "b": vector("u32", b)}}
    while True:
        yield {"environment": {"fp_mode": "ieee", "rounding": modes[random.next() % len(modes)]}, "generation": {"algorithm": "splitmix64", "class": "random", "seed": seed_text}, "operands": {"a": vector("u32", tuple(random.next() & MASK for _ in range(4))), "b": vector("u32", tuple(random.next() & MASK for _ in range(4)))}}


def execute(record: dict[str, JSONValue]) -> dict[str, JSONValue]:
    operands = record["operands"]; assert isinstance(operands, dict)
    a, b = operands["a"], operands["b"]; assert isinstance(a, dict) and isinstance(b, dict)
    left, right = a["lanes"], b["lanes"]; assert isinstance(left, list) and isinstance(right, list)
    values = tuple(int(str(left[index]), 16) * int(str(right[index]), 16) for index in (0, 2))
    return {"return": vector("u64", values)}
