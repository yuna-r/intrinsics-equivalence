"""Case pack for _mm_slli_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.slli.i16x8.imm8
description: logical left shift of eight 16-bit lanes using an imm8 count

intel:
  symbol: intel_mm_slli_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_slli_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i16, lanes: 8}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: i16, lanes: 8}

immediates:
  imm8:
    values: [0, 1, 7, 15, 16, 255]
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


CASE_ID, MINIMUM_COUNTS, candidates, execute = immediate_shift_case("sse2.slli.i16x8.imm8", "i16x8", "<<")
