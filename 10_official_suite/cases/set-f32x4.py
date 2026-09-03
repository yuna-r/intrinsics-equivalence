"""Case pack for _mm_set_ps."""

CASE_YAML = """
schema_version: 1
id: sse2.set.f32x4.high-low
description: construct four binary32 lanes from scalar bit patterns supplied high to low

intel:
  symbol: intel_mm_set_ps
  required_isa: [sse2]

openpower:
  symbol: power_mm_set_ps
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane3, type: scalar, element: f32}
    - {name: lane2, type: scalar, element: f32}
    - {name: lane1, type: scalar, element: f32}
    - {name: lane0, type: scalar, element: f32}
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
    "sse2.set.f32x4.high-low", "f32", ["lane3", "lane2", "lane1", "lane0"], reverse=True
)
