"""Case pack for _mm_cvtsi64_si128."""

CASE_YAML = """
schema_version: 1
id: sse2.cvtsi64.i64x2.default
description: place one signed 64-bit scalar in the low lane and clear the high lane

intel:
  symbol: intel_mm_cvtsi64_si128
  required_isa: [sse2]

openpower:
  symbol: power_mm_cvtsi64_si128
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: value, type: scalar, element: i64}
  return: {type: vector, element: i64, lanes: 2}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import scalar_vector_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = scalar_vector_case("sse2.cvtsi64.i64x2.default", "i64x2", "low")
