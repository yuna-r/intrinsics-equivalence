"""Case pack for _mm_cmpunord_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpunord.f64x2.scalar
description: test the low binary64 lanes for unordered operands while preserving the first operand's high lane

intel:
  symbol: intel_mm_cmpunord_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpunord_sd
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

tags: [lane-order-sensitive, nan-sensitive]
"""

from ioitf.casepack_families import float_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_compare_case("sse2.cmpunord.f64x2.scalar", "f64x2", "unord", scalar_only=True)
