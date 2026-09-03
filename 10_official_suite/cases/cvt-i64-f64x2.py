"""Case pack for _mm_cvtsi64_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.cvt.i64.f64x2.scalar
description: convert a signed 64-bit scalar into the low binary64 lane while preserving the high lane

intel:
  symbol: intel_mm_cvtsi64_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsi64_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: value, type: scalar, element: i64}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [lane-order-sensitive, signedness-sensitive]
"""

from ioitf.casepack_families import scalar_conversion_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_conversion_case("sse2.cvt.i64.f64x2.scalar", "i64", "f64x2")
