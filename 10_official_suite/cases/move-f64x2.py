"""Case pack for _mm_move_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.move.f64x2.default
description: replace the low binary64 lane while retaining the high lane

intel:
  symbol: intel_mm_move_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_move_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import lanes_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = lanes_case("sse2.move.f64x2.default", "f64x2", "b0 a1")
