"""Case pack for _mm_adds_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.adds.i16x8.default
description: add eight signed 16-bit lanes with signed saturation

intel:
  symbol: intel_mm_adds_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_adds_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i16, lanes: 8}
    - {name: b, type: vector, element: i16, lanes: 8}
  return: {type: vector, element: i16, lanes: 8}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.adds.i16x8.default", "i16x8", "sat+", standard=8)
