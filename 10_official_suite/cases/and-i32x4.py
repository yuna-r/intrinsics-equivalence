"""Case pack for _mm_and_si128."""

CASE_YAML = """
schema_version: 1
id: sse2.and.i32x4.default
description: bitwise AND across four 32-bit lanes

intel:
  symbol: intel_mm_and_si128
  required_isa: [sse2]

openpower:
  symbol: power_mm_and_si128
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i32, lanes: 4}
    - {name: b, type: vector, element: i32, lanes: 4}
  return: {type: vector, element: i32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import binary_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.and.i32x4.default", "i32x4", "&", standard=8)
