"""Development generator and executable model for _mm_cmpunord_ps."""

from __future__ import annotations

from typing import Iterator

from ioitf.canonical import JSONValue
from ioitf.cases import CaseDefinition
from ioitf.development import SplitMix64, rounding_modes, vector


CASE_ID = "sse2.cmpunord.f32x4.default"
MINIMUM_COUNTS = {"standard": 8}
TRUE_MASK = "0xffffffff"
FALSE_MASK = "0x00000000"
EXPONENT_MASK = 0x7F800000
FRACTION_MASK = 0x007FFFFF


def candidates(
    case: CaseDefinition, *, seed_text: str
) -> Iterator[dict[str, JSONValue]]:
    random = SplitMix64(int(seed_text, 16))
    modes = rounding_modes(case)
    structured = (
        ((0x3F800000, 0xC0200000, 0x00000000, 0x80000000),
         (0x3F800000, 0x40400000, 0x80000000, 0x00000000), "structured"),
        ((0x7F800000, 0xFF800000, 0x7F7FFFFF, 0xFF7FFFFF),
         (0x7F7FFFFF, 0x7F800000, 0xFF800000, 0x00000000), "boundary"),
        ((0x7FC00042, 0x3F800000, 0xFFC00043, 0xBF800000),
         (0x3F800000, 0x7FC01234, 0x40000000, 0xFFC05678), "boundary"),
        ((0x7F800001, 0xBF800000, 0xFF800001, 0x40000000),
         (0xBF800000, 0x7F800001, 0x40400000, 0xFF800001), "boundary"),
        ((0x00000001, 0x80000001, 0x007FFFFF, 0x807FFFFF),
         (0x00000000, 0x80000000, 0x00800000, 0x80800000), "boundary"),
        ((0xFFFFFFFF, 0x7FFFFFFF, 0xFF800000, 0x7F800000),
         (0x7F800000, 0xFF800000, 0xFFFFFFFF, 0x7FFFFFFF), "boundary"),
        ((0x7FC00000, 0xFFC00000, 0x7F800000, 0xFF800000),
         (0x7FC00000, 0xFFC00000, 0x7F800000, 0xFF800000), "boundary"),
        ((0x3EAAAAAB, 0xBEAAAAAB, 0x4B000001, 0xCB000001),
         (0x3EAAAAAA, 0xBEAAAAAA, 0x4B000000, 0xCB000000), "boundary"),
    )
    for index, (a, b, generation_class) in enumerate(structured):
        yield {
            "environment": {
                "fp_mode": "ieee",
                "rounding": modes[index % len(modes)],
            },
            "generation": {"class": generation_class},
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
                "a": vector("f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))),
                "b": vector("f32", tuple(random.next() & 0xFFFFFFFF for _ in range(4))),
            },
        }


def _is_nan(bits: int) -> bool:
    return bits & EXPONENT_MASK == EXPONENT_MASK and bool(bits & FRACTION_MASK)


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
        TRUE_MASK
        if _is_nan(int(str(a), 16)) or _is_nan(int(str(b), 16))
        else FALSE_MASK
        for a, b in zip(left_lanes, right_lanes, strict=True)
    ]
    return {"return": {"element": "f32", "lanes": lanes}}
