"""Development generator and executable model for _mm_cvtsi128_si64."""

from ioitf.casepack_families import low_scalar_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = low_scalar_case("sse2.cvtsi128.i64x2.low", "i64", 2)
