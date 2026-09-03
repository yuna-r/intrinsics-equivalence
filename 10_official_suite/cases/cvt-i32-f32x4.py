"""Case pack for _mm_cvtsi32_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.cvt.i32.f32x4.scalar
description: convert a signed 32-bit scalar into the low binary32 lane while preserving the upper lanes

intel:
  symbol: intel_mm_cvtsi32_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsi32_ss
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
    - {name: value, type: scalar, element: i32}
  return: {type: vector, element: f32, lanes: 4}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_conversion_case("sse2.cvt.i32.f32x4.scalar", "i32", "f32x4")
