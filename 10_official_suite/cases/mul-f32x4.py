"""Case pack for _mm_mul_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.mul.f32x4.default
description: four-lane IEEE 754 binary32 multiplication

intel:
  symbol: intel_mm_mul_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_mul_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
    - {name: b, type: vector, element: f32, lanes: 4}
  return: {type: vector, element: f32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [signed-zero-sensitive]
"""

from ioitf.casepack_families import float_binary_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_binary_case("sse2.mul.f32x4.default", "f32x4", "*")
