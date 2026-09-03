"""Case pack for _mm_cvttss_si32."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtt.f32x4.i32.scalar
description: truncate the low binary32 lane to a signed 32-bit scalar

intel:
  symbol: intel_mm_cvttss_si32
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvttss_si32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
  return: {type: scalar, element: i32}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_to_scalar_case("sse2.cvtt.f32x4.i32.scalar", "f32x4", "i32", truncate=True)
