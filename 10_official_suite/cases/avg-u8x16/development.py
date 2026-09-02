"""Development generator and executable model for _mm_avg_epu8."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0,) * 16, (0,) * 16),
    ((0, 1, 2, 3) * 4, (1, 2, 3, 4) * 4),
    ((0xFF, 0xFE, 0x80, 0x7F) * 4, (0xFF, 1, 0x80, 0x80) * 4),
    (tuple(range(16)), tuple(reversed(range(16)))),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.avg.u8x16.default", "u8x16", "avg", EXAMPLES,
    standard=4,
)
