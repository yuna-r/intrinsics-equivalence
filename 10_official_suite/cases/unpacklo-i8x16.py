"""Case pack for _mm_unpacklo_epi8."""

CASE_YAML = """
schema_version: 1
id: sse2.unpacklo.i8x16.default
description: interleave the low eight 8-bit lanes from two vectors

intel:
  symbol: intel_mm_unpacklo_epi8
  required_isa: [sse2]

openpower:
  symbol: power_mm_unpacklo_epi8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i8, lanes: 16}
    - {name: b, type: vector, element: i8, lanes: 16}
  return: {type: vector, element: i8, lanes: 16}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = lanes_case("sse2.unpacklo.i8x16.default", "i8x16", "ziplo")
