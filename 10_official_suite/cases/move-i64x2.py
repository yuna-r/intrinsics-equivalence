"""Case pack for _mm_move_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.move.i64x2.default
description: preserve the low signed 64-bit lane and clear the high lane

intel:
  symbol: intel_mm_move_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_move_epi64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i64, lanes: 2}
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

from ioitf.casepack_families import lanes_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = lanes_case("sse2.move.i64x2.default", "i64x2", "a0 0")
