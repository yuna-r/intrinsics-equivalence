"""Development generator and executable model for _mm_set_epi8."""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.i8x16.high-low", "i8", ["lane15","lane14","lane13","lane12","lane11","lane10","lane9","lane8","lane7","lane6","lane5","lane4","lane3","lane2","lane1","lane0"], reverse=True)
