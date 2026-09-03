"""Case pack for _mm_set1_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.set1.f32x4.default
description: broadcast one binary32 scalar bit pattern to four lanes

intel:
  symbol: intel_mm_set1_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_set1_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: f32}
  return: {type: vector, element: f32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import scalar_vector_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_vector_case(
    "sse2.set1.f32x4.default", "f32x4", "splat"
)
