"""Development generator and executable model for _mm_castps_si128."""

from ioitf.casepack_families import bitcast_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitcast_case("sse2.cast.f32x4.i32x4", "f32", 4, "i32", 4)
