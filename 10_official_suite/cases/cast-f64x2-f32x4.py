"""Case pack for _mm_castpd_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.cast.f64x2.f32x4
description: reinterpret the full 128-bit payload from f64 lanes to f32 lanes

intel:
  symbol: intel_mm_castpd_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_castpd_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import bitcast_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = bitcast_case("sse2.cast.f64x2.f32x4", "f64", 2, "f32", 4)
