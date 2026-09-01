"""Development generator and executable model for _mm_cmplt_epi16."""

from ioitf.casepack_families import signed_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = signed_compare_case("sse2.cmplt.i16x8.default", "i16", 8)
