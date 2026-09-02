"""Development generator and executable model for _mm_or_si128."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0, 0, 0, 0), (0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF)),
    ((0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF),
     (0, 0xFFFFFFFF, 0xAAAAAAAA, 0x55555555)),
    ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
     (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC)),
    ((0x80000000, 0x7FFFFFFF, 0x0000FFFF, 0xFFFF0000),
     (0x00000001, 0x80000000, 0xFFFF0000, 0x0000FFFF)),
    ((1, 2, 4, 8), (0x10, 0x20, 0x40, 0x80)),
    ((0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0x0BADF00D),
     (0x76543210, 0x11111111, 0x00FF00FF, 0xF0000000)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.or.i32x4.default", "i32x4", "|", EXAMPLES,
    standard=8,
    example_class="structured",
)
