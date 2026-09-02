"""Case pack for _mm_movemask_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.movemask.f32x4.default
description: collect the sign bit of each binary32 lane into a scalar mask

intel:
  symbol: intel_mm_movemask_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_movemask_ps
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

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import movemask_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = movemask_case("sse2.movemask.f32x4.default", "f32x4")
