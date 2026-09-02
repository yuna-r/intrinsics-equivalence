"""Case pack for _mm_cvtsi128_si32."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtsi128.i32x4.low
description: extract the low signed 32-bit lane as a scalar

intel:
  symbol: intel_mm_cvtsi128_si32
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsi128_si32
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: i32, lanes: 4}
  return: {type: scalar, element: i32}

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


CASE_ID, MINIMUM_COUNTS, candidates, execute = low_scalar_case("sse2.cvtsi128.i32x4.low", "i32", 4)
