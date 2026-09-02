"""Case pack for _mm_shuffle_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.shuffle.f64x2.imm8
description: select one binary64 lane from each input using an imm8 control

intel:
  symbol: intel_mm_shuffle_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_shuffle_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
    - {name: imm8, type: immediate, element: u8}
  return: {type: vector, element: f64, lanes: 2}

immediates:
  imm8:
    values: [0, 1, 2, 3]
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


CASE_ID, MINIMUM_COUNTS, candidates, execute = shuffle_case("sse2.shuffle.f64x2.imm8", "f64x2", "pair")
