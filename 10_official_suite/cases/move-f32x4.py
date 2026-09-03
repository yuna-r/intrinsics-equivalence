"""Case pack for _mm_move_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.move.f32x4.default
description: replace the low binary32 lane while preserving the other three lanes

intel:
  symbol: intel_mm_move_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_move_ss
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

tags: [lane-order-sensitive]
"""

from ioitf.casepack_families import lanes_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = lanes_case("sse2.move.f32x4.default", "f32x4", "b0 a1 a2 a3")
