"""Case pack for _mm_cvttsd_si64."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtt.f64x2.i64.scalar
description: truncate the low binary64 lane to a signed 64-bit scalar

intel:
  symbol: intel_mm_cvttsd_si64
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvttsd_si64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
  return: {type: scalar, element: i64}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [nan-sensitive, rounding-sensitive, signedness-sensitive]
"""

from ioitf.casepack_families import float_to_scalar_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_to_scalar_case("sse2.cvtt.f64x2.i64.scalar", "f64x2", "i64", truncate=True)
