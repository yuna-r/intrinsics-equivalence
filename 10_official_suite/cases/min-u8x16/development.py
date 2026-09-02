"""Development generator and executable model for _mm_min_epu8."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0,) * 16, (0xFF,) * 16),
    ((0, 1, 0x7F, 0x80) * 4, (1, 0, 0x80, 0x7F) * 4),
    (tuple(range(16)), tuple(reversed(range(16)))),
    ((0xAA, 0x55, 0xCC, 0x33) * 4, (0x55, 0xAA, 0x33, 0xCC) * 4),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.min.u8x16.default", "u8x16", "min", EXAMPLES,
    standard=4,
)
