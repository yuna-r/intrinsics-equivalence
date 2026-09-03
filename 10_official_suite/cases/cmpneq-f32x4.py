"""Case pack for _mm_cmpneq_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpneq.f32x4.default
description: compare four binary32 lanes for unordered inequality

intel:
  symbol: intel_mm_cmpneq_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpneq_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
    - {name: b, type: vector, element: f32, lanes: 4}
  return: {type: vector, element: f32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import float_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_compare_case("sse2.cmpneq.f32x4.default", "f32x4", "!=")
