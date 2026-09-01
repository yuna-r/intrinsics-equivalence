"""Development generator and executable model for _mm_sll_epi32."""

from ioitf.casepack_families import variable_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = variable_shift_case("sse2.sll.i32x4.vector-count", "i32", 4, "left")
