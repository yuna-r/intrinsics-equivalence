"""Development generator and executable model for _mm_and_si128."""

from ioitf.casepack_families import binary_case


EXAMPLES = (
    ((0xFFFFFFFF, 0x0F0F0F0F, 0xAAAAAAAA, 0x80000000),
     (0x12345678, 0xF0F0F0F0, 0x55555555, 0xFFFFFFFF)),
    ((0, 0, 0, 0), (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)),
    ((0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF),
     (0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF, 0xFFFFFFFF)),
    ((0xAAAAAAAA, 0x55555555, 0xCCCCCCCC, 0x33333333),
     (0x55555555, 0xAAAAAAAA, 0x33333333, 0xCCCCCCCC)),
    ((1, 2, 4, 8), (1, 3, 7, 15)),
    ((0x80000000, 0x7FFFFFFF, 0x0000FFFF, 0xFFFF0000),
     (0xFFFFFFFF, 0x80000000, 0xFFFF0000, 0x0000FFFF)),
    ((0x01234567, 0x89ABCDEF, 0xFEDCBA98, 0x76543210),
     (0x11111111, 0x22222222, 0x44444444, 0x88888888)),
    ((0xDEADBEEF, 0xCAFEBABE, 0x0BADF00D, 0xC001D00D),
     (0x00FF00FF, 0xFF00FF00, 0x33333333, 0x55555555)),
)

CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case(
    "sse2.and.i32x4.default", "i32x4", "&", EXAMPLES,
    standard=8,
    example_class="structured",
)
