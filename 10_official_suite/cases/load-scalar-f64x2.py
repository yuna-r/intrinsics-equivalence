"""Case pack for _mm_load_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.load.f64x2.scalar
description: load one binary64 value into the low lane and zero the upper lane

intel:
  symbol: intel_mm_load_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_load_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: source, type: pointer}
  return: {type: vector, element: f64, lanes: 2}

memory_contract:
  source:
    access: read
    read_ranges: [{offset: 0, byte_length: 8}]
    required_alignment: 1
    write_ranges: []

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import memory_load_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = memory_load_case(
    "sse2.load.f64x2.scalar", "f64x2", "scalar"
)
