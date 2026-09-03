"""Case pack for _mm_set1_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.set1.i16x8.default
description: broadcast one signed 16-bit scalar bit pattern to eight lanes

intel:
  symbol: intel_mm_set1_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_set1_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: i16}
  return: {type: vector, element: i16, lanes: 8}

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
    "sse2.set1.i16x8.default", "i16x8", "splat"
)
