"""Case pack for _mm_storeu_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.storeu.f32x4.default
description: store four binary32 lanes to unaligned memory in lane order

intel:
  symbol: intel_mm_storeu_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_storeu_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: destination, type: pointer}
    - {name: a, type: vector, element: f32, lanes: 4}
  return: {type: void}

memory_contract:
  destination:
    access: write
    read_ranges: []
    required_alignment: 1
    write_ranges: [{offset: 0, byte_length: 16}]

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import memory_store_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = memory_store_case(
    "sse2.storeu.f32x4.default", "f32x4", "all"
)
