"""Case pack for _mm_loadl_epi64."""

CASE_YAML = """
schema_version: 1
id: sse2.loadl.i64x2.zero-high
description: load one signed 64-bit lane from memory and zero the high lane

intel:
  symbol: intel_mm_loadl_epi64
  required_isa: [sse2]

openpower:
  symbol: power_mm_loadl_epi64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: source, type: pointer}
  return: {type: vector, element: i64, lanes: 2}

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

tags: [endianness-sensitive, signedness-sensitive]
"""

from ioitf.casepack_families import memory_load_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = memory_load_case(
    "sse2.loadl.i64x2.zero-high", "i64x2", "scalar"
)
