"""Case pack for _mm_insert_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.insert.i16x8.imm8
description: insert the low 16 bits of a scalar into an immediate-selected lane

intel:
  symbol: intel_mm_insert_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_insert_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i16, lanes: 8}
    - {name: value, type: scalar, element: i32}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: i16, lanes: 8}

immediates:
  imm8:
    values: [0, 1, 2, 3, 4, 5, 6, 7]
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

from ioitf.casepack_families import insert_i16_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = insert_i16_case("sse2.insert.i16x8.imm8")
