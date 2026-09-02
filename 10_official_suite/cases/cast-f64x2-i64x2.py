"""Case pack for _mm_castpd_si128."""

CASE_YAML = """
schema_version: 1
id: sse2.cast.f64x2.i64x2
description: reinterpret two binary64 lanes as 128 integer bits without conversion

intel:
  symbol: intel_mm_castpd_si128
  required_isa: [sse2]

openpower:
  symbol: power_mm_castpd_si128
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
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

from ioitf.casepack_families import bitcast_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitcast_case("sse2.cast.f64x2.i64x2", "f64", 2, "i64", 2)
