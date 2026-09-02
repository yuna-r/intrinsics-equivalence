"""Case pack for _mm_srai_epi32."""

CASE_YAML = """
schema_version: 1
id: sse2.srai.i32x4.imm8
description: arithmetic right shift of four signed 32-bit lanes using an imm8 count

intel:
  symbol: intel_mm_srai_epi32
  required_isa: [sse2]

openpower:
  symbol: power_mm_srai_epi32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i32, lanes: 4}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: i32, lanes: 4}

immediates:
  imm8:
    values: [0, 1, 15, 31, 32, 255]
    compile_time: true

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import immediate_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = immediate_shift_case("sse2.srai.i32x4.imm8", "i32x4", "s>>")
