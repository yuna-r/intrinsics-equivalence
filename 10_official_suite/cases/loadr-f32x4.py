"""Case pack for _mm_loadr_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.loadr.f32x4.reverse
description: load four aligned binary32 values from memory in reversed lane order

intel:
  symbol: intel_mm_loadr_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_loadr_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: source, type: pointer}
  return: {type: vector, element: f32, lanes: 4}

memory_contract:
  source:
    access: read
    read_ranges: [{offset: 0, byte_length: 16}]
    required_alignment: 16
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
    "sse2.loadr.f32x4.reverse", "f32x4", "reverse"
)
