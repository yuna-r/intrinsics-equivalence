"""Case pack for _mm_comilt_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.comilt.f64x2.scalar
description: scalar ordered/unordered binary64 comparison of the low lanes

intel:
  symbol: intel_mm_comilt_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_comilt_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
  return: {type: scalar, element: i32}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, nan-sensitive]
"""

from ioitf.casepack_families import comi_f64_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = comi_f64_case("sse2.comilt.f64x2.scalar", "lt")
