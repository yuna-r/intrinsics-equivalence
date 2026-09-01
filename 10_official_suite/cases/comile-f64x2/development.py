"""Development generator and executable model for _mm_comile_sd."""

from ioitf.casepack_families import comi_f64_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = comi_f64_case("sse2.comile.f64x2.scalar", "le")
