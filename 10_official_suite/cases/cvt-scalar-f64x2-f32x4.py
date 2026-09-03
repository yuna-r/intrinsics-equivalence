"""Case pack for _mm_cvtsd_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.cvt.f64x2.f32x4.scalar
description: narrow the low binary64 lane into binary32 while preserving the first operand's upper binary32 lanes

intel:
  symbol: intel_mm_cvtsd_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsd_ss
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
    - {name: b, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f32, lanes: 4}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_conversion_case("sse2.cvt.f64x2.f32x4.scalar", "f64x2", "f32x4")
