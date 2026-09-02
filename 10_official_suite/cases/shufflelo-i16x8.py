"""Case pack for _mm_shufflelo_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.shufflelo.i16x8.imm8
description: shuffle the low four signed 16-bit lanes using an imm8 control

intel:
  symbol: intel_mm_shufflelo_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_shufflelo_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i16, lanes: 8}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: i16, lanes: 8}

immediates:
  imm8:
    values: [0, 1, 27, 228, 255]
    compile_time: true

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import shuffle_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = shuffle_case("sse2.shufflelo.i16x8.imm8", "i16x8", "low")
