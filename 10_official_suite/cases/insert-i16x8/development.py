"""Development generator and executable model for _mm_insert_epi16."""

from ioitf.casepack_families import insert_i16_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = insert_i16_case("sse2.insert.i16x8.imm8")
