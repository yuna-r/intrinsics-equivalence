"""Development generator and executable model for _mm_sll_epi16."""

from ioitf.casepack_families import variable_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = variable_shift_case("sse2.sll.i16x8.vector-count", "i16", 8, "left")
