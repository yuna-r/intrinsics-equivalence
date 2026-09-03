"""Case pack for _mm_storeh_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.storeh.f64x2.high
description: store the high binary64 lane while leaving adjacent memory untouched

intel:
  symbol: intel_mm_storeh_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_storeh_pd
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
    "sse2.storeh.f64x2.high", "f64x2", "high"
)
