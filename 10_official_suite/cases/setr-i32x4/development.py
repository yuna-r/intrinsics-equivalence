"""Development generator and executable model for _mm_setr_epi32."""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.setr.i32x4.low-high", "i32", ["lane0", "lane1", "lane2", "lane3"], reverse=False)
