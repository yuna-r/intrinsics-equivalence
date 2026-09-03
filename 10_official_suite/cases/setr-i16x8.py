"""Case pack for _mm_setr_epi16."""

CASE_YAML = """
schema_version: 1
id: sse2.setr.i16x8.low-high
description: construct eight signed 16-bit lanes supplied low to high

intel:
  symbol: intel_mm_setr_epi16
  required_isa: [sse2]

openpower:
  symbol: power_mm_setr_epi16
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane0, type: scalar, element: i16}
    - {name: lane1, type: scalar, element: i16}
    - {name: lane2, type: scalar, element: i16}
    - {name: lane3, type: scalar, element: i16}
    - {name: lane4, type: scalar, element: i16}
    - {name: lane5, type: scalar, element: i16}
    - {name: lane6, type: scalar, element: i16}
    - {name: lane7, type: scalar, element: i16}
  return: {type: vector, element: i16, lanes: 8}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, signedness-sensitive]
"""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.setr.i16x8.low-high", "i16", ["lane0", "lane1", "lane2", "lane3", "lane4", "lane5", "lane6", "lane7"], reverse=False)
