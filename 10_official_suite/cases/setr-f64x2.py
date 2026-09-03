"""Case pack for _mm_setr_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.setr.f64x2.low-high
description: construct two binary64 lanes from scalar bit patterns supplied low to high

intel:
  symbol: intel_mm_setr_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_setr_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: lane0, type: scalar, element: f64}
    - {name: lane1, type: scalar, element: f64}
  return: {type: vector, element: f64, lanes: 2}

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
    "sse2.setr.f64x2.low-high", "f64", ["lane0", "lane1"], reverse=False
)
