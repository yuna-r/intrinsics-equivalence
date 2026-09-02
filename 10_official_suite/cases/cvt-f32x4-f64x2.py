"""Case pack for _mm_cvtps_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.cvt.f32x4.f64x2
description: widen the low two binary32 lanes to exact binary64 values

intel:
  symbol: intel_mm_cvtps_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtps_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
  return: {type: vector, element: f64, lanes: 2}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = conversion_case("sse2.cvt.f32x4.f64x2", "f32x4", "f64x2")
