"""Case pack for _mm_set1_epi8."""

CASE_YAML = """
schema_version: 1
id: sse2.set1.i8x16.default
description: broadcast one signed 8-bit scalar bit pattern to sixteen lanes

intel:
  symbol: intel_mm_set1_epi8
  required_isa: [sse2]

openpower:
  symbol: power_mm_set1_epi8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: i8}
  return: {type: vector, element: i8, lanes: 16}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [signedness-sensitive]
"""

from ioitf.casepack_families import scalar_vector_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_vector_case(
    "sse2.set1.i8x16.default", "i8x16", "splat"
)
