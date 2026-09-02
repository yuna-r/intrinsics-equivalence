"""Case pack for _mm_cmpeq_epi8."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpeq.i8x16.default
description: equality comparison across sixteen 8-bit lanes

intel:
  symbol: intel_mm_cmpeq_epi8
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpeq_epi8
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

tags: []
"""

from ioitf.casepack_families import binary_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.cmpeq.i8x16.default", "i8x16", "==", standard=8)
