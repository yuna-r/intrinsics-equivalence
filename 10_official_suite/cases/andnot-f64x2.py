"""Case pack for _mm_andnot_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.andnot.f64x2.default
description: bitwise AND of the second binary64 vector with the complement of the first

intel:
  symbol: intel_mm_andnot_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_andnot_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import bitwise_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitwise_case("sse2.andnot.f64x2.default", "f64x2", "~&")
