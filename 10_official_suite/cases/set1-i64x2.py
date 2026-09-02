"""Case pack for _mm_set1_epi64x."""

CASE_YAML = """
schema_version: 1
id: sse2.set1.i64x2.default
description: broadcast one signed 64-bit scalar bit pattern to two lanes

intel:
  symbol: intel_mm_set1_epi64x
  required_isa: [sse2]

openpower:
  symbol: power_mm_set1_epi64x
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: i64}
  return: {type: vector, element: i64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import scalar_vector_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_vector_case("sse2.set1.i64x2.default", "i64x2", "splat")
