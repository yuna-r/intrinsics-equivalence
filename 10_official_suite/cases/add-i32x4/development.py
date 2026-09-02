"""Development generator and executable model for _mm_add_epi32."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0, 0, 0, 0), (0, 0, 0, 0)),
    ((0x7FFFFFFF, 0x80000000, 0xFFFFFFFF, 1), (1, 0xFFFFFFFF, 1, 0xFFFFFFFF)),
    ((0x7FFFFFFF, 0x80000000, 0x40000000, 0xC0000000),
     (0x7FFFFFFF, 0x80000000, 0x40000000, 0xC0000000)),
    ((0xFFFFFFFF, 1, 0xFFFFFFFE, 2), (1, 0xFFFFFFFF, 2, 0xFFFFFFFE)),
    ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
     (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC)),
    ((0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0x0000FFFF),
     (0x76543210, 0x11111111, 0x21524111, 0xFFFF0001)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.add.i32x4.default", "i32x4", "+", EXAMPLES,
    standard=8,
    example_class="structured",
)
