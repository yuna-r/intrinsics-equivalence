"""Case pack for _mm_sqrt_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.sqrt.f64x2.default
description: two-lane IEEE 754 binary64 square root with SSE special-value results

intel:
  symbol: intel_mm_sqrt_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_sqrt_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import sqrt_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = sqrt_case("sse2.sqrt.f64x2.default", "f64x2")
