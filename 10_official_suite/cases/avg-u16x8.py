"""Case pack for _mm_avg_epu16."""

CASE_YAML = """
schema_version: 1
id: sse2.avg.u16x8.default
description: rounded average of eight unsigned 16-bit lanes

intel:
  symbol: intel_mm_avg_epu16
  required_isa: [sse2]

openpower:
  symbol: power_mm_avg_epu16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: u16, lanes: 8}
    - {name: b, type: vector, element: u16, lanes: 8}
  return: {type: vector, element: u16, lanes: 8}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import binary_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.avg.u16x8.default", "u16x8", "avg", standard=4)
