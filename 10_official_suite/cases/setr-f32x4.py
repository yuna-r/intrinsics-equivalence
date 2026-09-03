"""Case pack for _mm_setr_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.setr.f32x4.low-high
description: construct four binary32 lanes from scalar bit patterns supplied low to high

intel:
  symbol: intel_mm_setr_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_setr_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane0, type: scalar, element: f32}
    - {name: lane1, type: scalar, element: f32}
    - {name: lane2, type: scalar, element: f32}
    - {name: lane3, type: scalar, element: f32}
  return: {type: vector, element: f32, lanes: 4}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import set_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case(
    "sse2.setr.f32x4.low-high", "f32", ["lane0", "lane1", "lane2", "lane3"], reverse=False
)
