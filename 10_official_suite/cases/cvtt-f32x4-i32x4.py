"""Case pack for _mm_cvttps_epi32."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtt.f32x4.i32x4
description: truncate four binary32 lanes to signed 32-bit integers

intel:
  symbol: intel_mm_cvttps_epi32
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvttps_epi32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
  return: {type: vector, element: i32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import conversion_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = conversion_case("sse2.cvtt.f32x4.i32x4", "f32x4", "i32x4", truncate=True)
