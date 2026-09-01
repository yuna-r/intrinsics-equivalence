"""Development generator and executable model for _mm_castps_pd."""

from ioitf.casepack_families import bitcast_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitcast_case("sse2.cast.f32x4.f64x2", "f32", 4, "f64", 2)
