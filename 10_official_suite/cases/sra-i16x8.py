"""Case pack for _mm_sra_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.sra.i16x8.vector-count
description: arithmetic right shift using the low 64-bit lane of a vector count

intel:
  symbol: intel_mm_sra_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_sra_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i16, lanes: 8}
    - {name: count, type: vector, element: u64, lanes: 2}
  return: {type: vector, element: i16, lanes: 8}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import variable_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = variable_shift_case("sse2.sra.i16x8.vector-count", "i16", 8, "arithmetic-right")
