"""Case pack for _mm_avg_epu8."""

CASE_YAML = """
schema_version: 1
id: sse2.avg.u8x16.default
description: rounded average of sixteen unsigned 8-bit lanes

intel:
  symbol: intel_mm_avg_epu8
  required_isa: [sse2]

openpower:
  symbol: power_mm_avg_epu8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: u8, lanes: 16}
    - {name: b, type: vector, element: u8, lanes: 16}
  return: {type: vector, element: u8, lanes: 16}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = binary_case("sse2.avg.u8x16.default", "u8x16", "avg", standard=4)
