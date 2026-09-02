"""Development generator and executable model for _mm_avg_epu16."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0,) * 8, (0,) * 8),
    ((0, 1, 2, 3, 4, 5, 6, 7), (1, 2, 3, 4, 5, 6, 7, 8)),
    ((0xFFFF, 0xFFFE, 0x8000, 0x7FFF) * 2, (0xFFFF, 1, 0x8000, 0x8000) * 2),
    ((0xAAAA, 0x5555, 0x1234, 0xFEDC, 0x0101, 0x1010, 0xFFFF, 2), (0x5555, 0xAAAA, 0xFEDC, 0x1234, 0x1010, 0x0101, 2, 0xFFFF)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.avg.u16x8.default", "u16x8", "avg", EXAMPLES,
    standard=4,
)
