"""Case pack for _mm_cvtsi128_si64."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtsi128.i64x2.low
description: extract the low signed 64-bit lane as a scalar

intel:
  symbol: intel_mm_cvtsi128_si64
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsi128_si64
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i64, lanes: 2}
  return: {type: scalar, element: i64}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import low_scalar_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = low_scalar_case("sse2.cvtsi128.i64x2.low", "i64", 2)
