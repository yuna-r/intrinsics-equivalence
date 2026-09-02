"""Development generator and executable model for _mm_cmpeq_epi32."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0, 0, 0, 0), (0, 0, 0, 0)),
    ((0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 1),
     (0xFFFFFFFF, 0x80000000, 0x7FFFFFFF, 1)),
    ((0, 1, 0xFFFFFFFF, 0x80000000), (1, 0, 0x7FFFFFFF, 0x80000001)),
    ((0, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF),
     (0, 0, 0x80000000, 0xFFFFFFFF)),
    ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
     (0xAAAAAAAA, 0xAAAAAAAA, 0xCCCCCCCC, 0xCCCCCCCC)),
    ((0x01234567, 0x89ABCDEF, 0xDEADBEEF, 0x0BADF00D),
     (0x01234567, 0x89ABCDEE, 0xDEADBEEF, 0x0BADF00C)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.cmpeq.i32x4.default", "i32x4", "==", EXAMPLES,
    standard=8,
    example_class="structured",
)
