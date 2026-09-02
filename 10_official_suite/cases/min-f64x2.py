"""Case pack for _mm_min_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.min.f64x2.default
description: packed binary64 minimum with SSE2 NaN and signed-zero selection semantics

intel:
  symbol: intel_mm_min_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_min_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f64, lanes: 2}
    - {name: b, type: vector, element: f64, lanes: 2}
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

from ioitf.casepack_families import minmax_f64_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = minmax_f64_case("sse2.min.f64x2.default", "min")
