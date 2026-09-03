"""Case pack for _mm_cvtss_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.cvt.f32x4.f64x2.scalar
description: widen the low binary32 lane into binary64 while preserving the first operand's high binary64 lane

intel:
  symbol: intel_mm_cvtss_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtss_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f32, lanes: 4}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [lane-order-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import scalar_conversion_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_conversion_case("sse2.cvt.f32x4.f64x2.scalar", "f32x4", "f64x2")
