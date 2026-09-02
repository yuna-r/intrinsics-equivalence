"""Case pack for _mm_cmpge_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpge.f64x2.default
description: compare two binary64 lanes for ordered greater-than-or-equal

intel:
  symbol: intel_mm_cmpge_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpge_pd
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

from ioitf.casepack_families import float_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_compare_case("sse2.cmpge.f64x2.default", "f64x2", ">=")
