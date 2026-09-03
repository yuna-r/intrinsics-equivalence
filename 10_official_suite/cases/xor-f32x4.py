"""Case pack for _mm_xor_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.xor.f32x4.default
description: bitwise XOR across four binary32 lanes

intel:
  symbol: intel_mm_xor_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_xor_ps
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

tags: []
"""

from ioitf.casepack_families import bitwise_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitwise_case("sse2.xor.f32x4.default", "f32x4", "^")
