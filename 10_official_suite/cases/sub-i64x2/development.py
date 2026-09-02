"""Development generator and executable model for _mm_sub_epi64."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0, 0), (0, 0)),
    ((0x8000000000000000, 0x7FFFFFFFFFFFFFFF), (1, 0xFFFFFFFFFFFFFFFF)),
    ((0, 0xFFFFFFFFFFFFFFFF), (1, 0xFFFFFFFFFFFFFFFF)),
    ((0xAAAAAAAAAAAAAAAA, 0x0123456789ABCDEF), (0x5555555555555555, 0xFEDCBA9876543210)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.sub.i64x2.default", "i64x2", "-", EXAMPLES,
    standard=4,
)
