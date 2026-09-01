"""Development generator and executable model for _mm_cvtsi128_si32."""

from ioitf.casepack_families import low_scalar_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = low_scalar_case("sse2.cvtsi128.i32x4.low", "i32", 4)
