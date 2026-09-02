"""Case pack for _mm_set1_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.set1.f64x2.default
description: broadcast one binary64 bit pattern to two lanes

intel:
  symbol: intel_mm_set1_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_set1_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: f64}
  return: {type: vector, element: f64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: []
"""

from ioitf.casepack_families import scalar_vector_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_vector_case("sse2.set1.f64x2.default", "f64x2", "splat")
