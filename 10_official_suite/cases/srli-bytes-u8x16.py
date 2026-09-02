"""Case pack for _mm_srli_si128."""

CASE_YAML = """
schema_version: 1
id: sse2.srli-bytes.u8x16.imm8
description: shift one 128-bit vector toward lower lane indexes by an immediate byte count

intel:
  symbol: intel_mm_srli_si128
  required_isa: [sse2]

openpower:
  symbol: power_mm_srli_si128
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: u8, lanes: 16}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: u8, lanes: 16}

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

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import immediate_shift_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = immediate_shift_case("sse2.srli-bytes.u8x16.imm8", "u8x16", "bytes>>")
