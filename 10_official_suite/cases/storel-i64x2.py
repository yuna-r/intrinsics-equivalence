"""Case pack for _mm_storel_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.storel.i64x2.low
description: store the low signed 64-bit lane while leaving adjacent memory untouched

intel:
  symbol: intel_mm_storel_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_storel_epi64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: destination, type: pointer}
    - {name: a, type: vector, element: i64, lanes: 2}
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

tags: [endianness-sensitive, signedness-sensitive]
"""

from ioitf.casepack_families import memory_store_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = memory_store_case(
    "sse2.storel.i64x2.low", "i64x2", "low"
)
