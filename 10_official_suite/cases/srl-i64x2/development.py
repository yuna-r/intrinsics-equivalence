"""Development generator and executable model for _mm_srl_epi64."""

from ioitf.casepack_families import variable_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = variable_shift_case("sse2.srl.i64x2.vector-count", "i64", 2, "logical-right")
