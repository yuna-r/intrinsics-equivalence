"""Case pack for _mm_store_sd."""

CASE_YAML = """
schema_version: 1
id: sse2.store.f64x2.scalar
description: store only the low binary64 lane to memory

intel:
  symbol: intel_mm_store_sd
  required_isa: [sse2]

openpower:
  symbol: power_mm_store_sd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: destination, type: pointer}
    - {name: a, type: vector, element: f64, lanes: 2}
  return: {type: void}

memory_contract:
  destination:
    access: write
    read_ranges: []
    required_alignment: 1
    write_ranges: [{offset: 0, byte_length: 8}]

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
    "sse2.store.f64x2.scalar", "f64x2", "low"
)
