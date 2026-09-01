"""Development generator and executable model for _mm_cmplt_epi8."""

from ioitf.casepack_families import signed_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = signed_compare_case("sse2.cmplt.i8x16.default", "i8", 16)
