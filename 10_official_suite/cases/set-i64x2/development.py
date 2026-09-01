"""Development generator and executable model for _mm_set_epi64."""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.i64x2.high-low", "i64", ["lane1","lane0"], reverse=True)
