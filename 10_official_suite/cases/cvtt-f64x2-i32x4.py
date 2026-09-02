"""Case pack for _mm_cvttpd_epi32."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtt.f64x2.i32x4
description: truncate two binary64 lanes to signed 32-bit integers and zero the high lanes

intel:
  symbol: intel_mm_cvttpd_epi32
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvttpd_epi32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: i32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import conversion_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = conversion_case("sse2.cvtt.f64x2.i32x4", "f64x2", "i32x4", truncate=True)
