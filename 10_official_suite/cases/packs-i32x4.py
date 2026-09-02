"""Case pack for _mm_packs_epi32."""

CASE_YAML = """
schema_version: 1
id: sse2.packs.i32x4.default
description: pack two signed 32-bit vectors into signed 16-bit lanes with saturation

intel:
  symbol: intel_mm_packs_epi32
  required_isa: [sse2]

openpower:
  symbol: power_mm_packs_epi32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i32, lanes: 4}
    - {name: b, type: vector, element: i32, lanes: 4}
  return: {type: vector, element: i16, lanes: 8}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import pack_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = pack_case("sse2.packs.i32x4.default", "i32x4", "i16x8")
