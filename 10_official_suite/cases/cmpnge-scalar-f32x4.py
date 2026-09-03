"""Case pack for _mm_cmpnge_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.cmpnge.f32x4.scalar
description: compare the low binary32 lanes for not-greater-than-or-equal, including unordered operands, while preserving upper lanes

intel:
  symbol: intel_mm_cmpnge_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_cmpnge_ss
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

tags: [lane-order-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import float_compare_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = float_compare_case("sse2.cmpnge.f32x4.scalar", "f32x4", "!>=", scalar_only=True)
