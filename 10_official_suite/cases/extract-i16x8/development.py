"""Development generator and executable model for _mm_extract_epi16."""

from ioitf.casepack_families import extract_i16_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = extract_i16_case("sse2.extract.i16x8.imm8")
