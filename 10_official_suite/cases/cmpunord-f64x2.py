"""Case pack for _mm_cmpunord_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpunord.f64x2.default
description: test two binary64 lanes for unordered operands

intel:
  symbol: intel_mm_cmpunord_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpunord_pd
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


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_compare_case("sse2.cmpunord.f64x2.default", "f64x2", "unord")
