"""Case pack for _mm_set_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.set.f64x2.high-low
description: construct a binary64 vector from explicit high and low scalar bit patterns

intel:
  symbol: intel_mm_set_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_set_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: high, type: scalar, element: f64}
    - {name: low, type: scalar, element: f64}
  return: {type: vector, element: f64, lanes: 2}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = set_case("sse2.set.f64x2.high-low", "f64", ["high", "low"], reverse=True)
