"""Development generator and executable model for _mm_max_pd."""

from ioitf.casepack_families import minmax_f64_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = minmax_f64_case("sse2.max.f64x2.default", "max")
