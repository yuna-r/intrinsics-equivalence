"""Case pack for _mm_setr_epi8."""

CASE_YAML = """
schema_version: 1
id: sse2.setr.i8x16.low-high
description: construct sixteen signed 8-bit lanes supplied low to high

intel:
  symbol: intel_mm_setr_epi8
  required_isa: [sse2]

openpower:
  symbol: power_mm_setr_epi8
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane0, type: scalar, element: i8}
    - {name: lane1, type: scalar, element: i8}
    - {name: lane2, type: scalar, element: i8}
    - {name: lane3, type: scalar, element: i8}
    - {name: lane4, type: scalar, element: i8}
    - {name: lane5, type: scalar, element: i8}
    - {name: lane6, type: scalar, element: i8}
    - {name: lane7, type: scalar, element: i8}
    - {name: lane8, type: scalar, element: i8}
    - {name: lane9, type: scalar, element: i8}
    - {name: lane10, type: scalar, element: i8}
    - {name: lane11, type: scalar, element: i8}
    - {name: lane12, type: scalar, element: i8}
    - {name: lane13, type: scalar, element: i8}
    - {name: lane14, type: scalar, element: i8}
    - {name: lane15, type: scalar, element: i8}
  return: {type: vector, element: i8, lanes: 16}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.setr.i8x16.low-high", "i8", ["lane0", "lane1", "lane2", "lane3", "lane4", "lane5", "lane6", "lane7", "lane8", "lane9", "lane10", "lane11", "lane12", "lane13", "lane14", "lane15"], reverse=False)
