"""Case pack for _mm_add_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.add.i64x2.default
description: add two signed 64-bit lanes with modulo-2^64 wrapping

intel:
  symbol: intel_mm_add_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_add_epi64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i64, lanes: 2}
    - {name: b, type: vector, element: i64, lanes: 2}
  return: {type: vector, element: i64, lanes: 2}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.add.i64x2.default", "i64x2", "+", standard=4)
