"""Development generator and executable model for _mm_set_epi32."""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.i32x4.high-low", "i32", ["lane3","lane2","lane1","lane0"], reverse=True)
