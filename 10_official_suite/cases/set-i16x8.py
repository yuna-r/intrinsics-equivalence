"""Case pack for _mm_set_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.set.i16x8.high-low
description: construct a vector from explicit scalar lanes supplied high to low

intel:
  symbol: intel_mm_set_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_set_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane7, type: scalar, element: i16}
    - {name: lane6, type: scalar, element: i16}
    - {name: lane5, type: scalar, element: i16}
    - {name: lane4, type: scalar, element: i16}
    - {name: lane3, type: scalar, element: i16}
    - {name: lane2, type: scalar, element: i16}
    - {name: lane1, type: scalar, element: i16}
    - {name: lane0, type: scalar, element: i16}
  return: {type: vector, element: i16, lanes: 8}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.i16x8.high-low", "i16", ["lane7","lane6","lane5","lane4","lane3","lane2","lane1","lane0"], reverse=True)
