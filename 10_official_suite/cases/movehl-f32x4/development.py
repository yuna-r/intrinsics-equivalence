"""Development generator and executable model for _mm_movehl_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.movehl.f32x4.default"
MINIMUM_COUNTS = {"standard": 6}


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0, 1, 2, 3), (4, 5, 6, 7)),
        (
            (0x00000000, 0x80000000, 0x7F800000, 0xFF800000),
            (0x7FC00042, 0xFFC00043, 0x7F800001, 0xFF800002),
        ),
        (
            (0x00000001, 0x007FFFFF, 0x00800000, 0x7F7FFFFF),
            (0x80000001, 0x807FFFFF, 0x80800000, 0xFF7FFFFF),
        ),
        (
            (0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
            (0x13579BDF, 0x2468ACE0, 0xAAAAAAAA, 0x55555555),
        ),
        (
            (0xFFFFFFFF, 0xEEEEEEEE, 0xDDDDDDDD, 0xCCCCCCCC),
            (0x11111111, 0x22222222, 0x33333333, 0x44444444),
        ),
        (
            (0x3F800000, 0xBF800000, 0x40000000, 0xC0000000),
            (0x40400000, 0xC0400000, 0x40800000, 0xC0800000),
        ),
    )
    for index, (a, b) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": "boundary"},
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
    assert isinstance(operands, dict)
    left = operands["a"]
    right = operands["b"]
    assert isinstance(left, dict) and isinstance(right, dict)
    a = left["lanes"]
    b = right["lanes"]
    assert isinstance(a, list) and isinstance(b, list)
    return {
        "return": vector(
            "f32",
            tuple(int(str(bits), 16) for bits in (b[2], b[3], a[2], a[3])),
        )
    }
