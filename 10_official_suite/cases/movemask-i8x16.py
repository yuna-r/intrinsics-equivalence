"""Case pack for _mm_movemask_epi8."""

CASE_YAML = """
schema_version: 1
id: sse2.movemask.i8x16.default
description: collect the sign bit of each signed 8-bit lane into a scalar mask

intel:
  symbol: intel_mm_movemask_epi8
  required_isa: [sse2]

openpower:
  symbol: power_mm_movemask_epi8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i8, lanes: 16}
  return: {type: scalar, element: i32}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import movemask_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = movemask_case("sse2.movemask.i8x16.default", "i8x16")
