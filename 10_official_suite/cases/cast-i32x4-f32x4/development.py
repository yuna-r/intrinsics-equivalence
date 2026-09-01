"""Development generator and executable model for _mm_castsi128_ps."""

from ioitf.casepack_families import bitcast_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitcast_case("sse2.cast.i32x4.f32x4", "i32", 4, "f32", 4)
