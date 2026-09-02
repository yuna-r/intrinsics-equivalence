"""Case pack for _mm_unpacklo_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.unpacklo.i64x2.default
description: interleave the low signed 64-bit lane from two vectors

intel:
  symbol: intel_mm_unpacklo_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_unpacklo_epi64
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

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import lanes_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = lanes_case("sse2.unpacklo.i64x2.default", "i64x2", "ziplo")
