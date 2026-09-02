"""Case pack for _mm_sad_epu8."""

CASE_YAML = """
schema_version: 1
id: sse2.sad.u8x16.default
description: sum absolute unsigned 8-bit differences independently across both 64-bit halves

intel:
  symbol: intel_mm_sad_epu8
  required_isa: [sse2]

openpower:
  symbol: power_mm_sad_epu8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: u8, lanes: 16}
    - {name: b, type: vector, element: u8, lanes: 16}
  return: {type: vector, element: u64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import reduce_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = reduce_case("sse2.sad.u8x16.default", "u8x16", "sad8")
