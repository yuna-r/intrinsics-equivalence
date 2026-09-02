"""Case pack for _mm_loadu_pd."""

CASE_YAML = """
schema_version: 1
id: sse2.loadu.f64x2.default
description: unaligned 16-byte load into two binary64 lanes

intel:
  symbol: intel_mm_loadu_pd
  required_isa: [sse2]

openpower:
  symbol: power_mm_loadu_pd
  required_isa: [power8, vsx]

signature:
  arguments:
    - {name: source, type: pointer}
  return: {type: vector, element: f64, lanes: 2}

memory_contract:
  source:
    access: read
    read_ranges:
      - {offset: 0, byte_length: 16}
    required_alignment: 1
    write_ranges: []

input_domain:
  exclude: []

comparison:
  mode: bit_exact

environment:
  fp_rounding_modes: [nearest_even]
  observe_fp_exceptions: false

tags: [endianness-sensitive]
"""

from ioitf.casepack_families import loadu_f64_case


CASE_ID, MINIMUM_COUNTS, candidates, execute = loadu_f64_case("sse2.loadu.f64x2.default")
