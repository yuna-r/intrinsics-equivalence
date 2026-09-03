"""Case pack for _mm_sqrt_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.sqrt.f32x4.scalar
description: square-root the low binary32 lane while preserving the upper lanes

intel:
  symbol: intel_mm_sqrt_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_sqrt_ss
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
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

from ioitf.casepack_families import sqrt_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = sqrt_case("sse2.sqrt.f32x4.scalar", "f32x4", scalar_only=True)
