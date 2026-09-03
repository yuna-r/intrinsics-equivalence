"""Case pack for _mm_loadr_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.loadr.f64x2.reverse
description: load two aligned binary64 values from memory in reversed lane order

intel:
  symbol: intel_mm_loadr_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_loadr_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: source, type: pointer}
  return: {type: vector, element: f64, lanes: 2}

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
    "sse2.loadr.f64x2.reverse", "f64x2", "reverse"
)
