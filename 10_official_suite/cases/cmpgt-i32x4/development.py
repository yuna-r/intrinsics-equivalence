"""Development generator and executable model for _mm_cmpgt_epi32."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    (
        (0, 1, 0xFFFFFFFF, 0x7FFFFFFF),
        (0, 0, 0, 0x80000000),
        "structured",
    ),
    (
        (0x80000000, 0x7FFFFFFF, 0xFFFFFFFF, 0),
        (0x7FFFFFFF, 0x80000000, 0, 0xFFFFFFFF),
        "boundary",
    ),
    (
        (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
        (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
        "boundary",
    ),
    (
        (1, 0xFFFFFFFE, 0x40000000, 0xC0000000),
        (0xFFFFFFFF, 0xFFFFFFFF, 0x3FFFFFFF, 0xBFFFFFFF),
        "boundary",
    ),
    (
        (0x80000001, 0xFFFFFFFE, 1, 0x7FFFFFFE),
        (0x80000000, 0xFFFFFFFF, 2, 0x7FFFFFFF),
        "boundary",
    ),
    (
        (0xAAAAAAAA, 0x55555555, 0xDEADBEEF, 0x01234567),
        (0x55555555, 0xAAAAAAAA, 0xCAFEBABE, 0x89ABCDEF),
        "structured",
    ),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.cmpgt.i32x4.default", "i32x4", ">", EXAMPLES,
    standard=8,
)
