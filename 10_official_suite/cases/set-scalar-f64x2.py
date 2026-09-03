"""Case pack for _mm_set_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.set.f64x2.scalar
description: place one binary64 scalar bit pattern in lane zero and zero the high lane

intel:
  symbol: intel_mm_set_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_set_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: f64}
  return: {type: vector, element: f64, lanes: 2}

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
    "sse2.set.f64x2.scalar", "f64x2", "low"
)
