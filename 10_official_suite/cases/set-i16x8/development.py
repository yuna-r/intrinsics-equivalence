"""Development generator and executable model for _mm_set_epi16."""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.i16x8.high-low", "i16", ["lane7","lane6","lane5","lane4","lane3","lane2","lane1","lane0"], reverse=True)
