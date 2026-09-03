"""Case pack for _mm_comieq_ss."""

CASE_YAML = """
schema_version: 1
id: sse2.comieq.f32x4.scalar
description: compare low binary32 lanes for ordered equality and return a scalar flag

intel:
  symbol: intel_mm_comieq_ss
  required_isa: [sse2]

openpower:
  symbol: power_mm_comieq_ss
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: a, type: vector, element: f32, lanes: 4}
    - {name: b, type: vector, element: f32, lanes: 4}
  return: {type: scalar, element: i32}

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive, nan-sensitive, signed-zero-sensitive]
"""

from ioitf.casepack_families import comi_f32_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = comi_f32_case(
    "sse2.comieq.f32x4.scalar", "eq"
)
