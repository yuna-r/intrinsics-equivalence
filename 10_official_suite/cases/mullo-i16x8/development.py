"""Development generator and executable model for _mm_mullo_epi16."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0, 1, 0xFFFF, 0x7FFF, 0x8000, 2, 0xFFFE, 0x4000), (0, 1, 2, 2, 2, 0xFFFF, 0x8000, 4)),
    ((0x7FFF,) * 8, (0x7FFF, 0x8000, 1, 2, 3, 4, 0xFFFF, 0)),
    ((0x8000,) * 8, (0x8000, 0x7FFF, 1, 2, 3, 4, 0xFFFF, 0)),
    ((0xAAAA, 0x5555, 0x1234, 0xFEDC, 0x0101, 0x1010, 0xFFFF, 2), (0x5555, 0xAAAA, 0xFEDC, 0x1234, 0x1010, 0x0101, 2, 0xFFFF)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.mullo.i16x8.default", "i16x8", "*lo", EXAMPLES,
    standard=4,
)
