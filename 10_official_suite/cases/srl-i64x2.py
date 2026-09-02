"""Case pack for _mm_srl_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.srl.i64x2.vector-count
description: logical right shift using the low 64-bit lane of a vector count

intel:
  symbol: intel_mm_srl_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_srl_epi64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i64, lanes: 2}
    - {name: count, type: vector, element: u64, lanes: 2}
  return: {type: vector, element: i64, lanes: 2}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = variable_shift_case("sse2.srl.i64x2.vector-count", "i64", 2, "logical-right")
