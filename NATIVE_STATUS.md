# Native implementation status

This directory implements the first native slice of IOITF-SPEC-001 section 6.

The development suite contains 24 case packs. This native slice currently
covers `_mm_add_pd`, `_mm_set1_pd`, and `_mm_shuffle_epi32`; the other case
packs remain development-fixture-only until architecture adapters are added.

Implemented:

- ABI version 1 C structs, enum values, LP64 sizes, and every normative
  `offsetof` assertion.
- Strict, case-specific decoding of the RFC 8785 byte representation used by
  `_mm_add_pd`, `_mm_set1_pd`, and `_mm_shuffle_epi32`. The decoder deliberately
  accepts only each complete canonical signature and the registered shuffle
  immediates; it is not a general JSON parser.
- The output-capacity handshake. A too-small first call publishes the exact
  required size and does not call the SUT.
- Canonical f64x2 return encoding, logical lane conversion, requested rounding
  mode, and normalized IEEE exception flags. Native input preparation occurs
  before flags are cleared; the observation interval invokes only the target
  operation; native result extraction occurs after flags are captured.
- The three native-slice cases have `observe_fp_exceptions: false`, so their public ABI
  output is always zero. The same internal capture path is independently tested
  through a test-only side channel, including the `inexact` bit.
- Linux x86_64 SSE2 adapters with public add, broadcast, and immediate-shuffle
  symbols. Shuffle uses a literal dispatch for `0`, `1`, `27`, and `255`.
- A canonical but undeclared `imm8` is returned as
  `IOITF_CALL_OK`/`IOITF_OUTPUT_INVALID_INPUT` without invoking the SUT;
  malformed or noncanonical ABI bytes remain `IOITF_CALL_INVALID_ABI`.
- A Linux ppc64le VSX compatibility implementation boundary with the public symbols
  `power_mm_add_pd`, `power_mm_set1_pd`, and `power_mm_shuffle_epi32`.
- Reader-facing VSX examples for all 24 official cases under
  `10_official_suite/openpower/`. On Linux ppc64le the two grouped source files
  are compiled as the `ioitf_openpower_official_suite` object target.
- A scalar portable adapter and self-test for development hosts such as arm64
  macOS. Its `portable_*` symbols are fixtures and must never be recorded as
  Intel or OpenPOWER evidence.

The native self-test covers ABI rejection, rejection of a noncanonical payload,
the exact-size retry protocol, output bounds, lane-independent known results,
negative-zero replication, all registered immediate shuffles, dynamic rounding,
and the inexact flag.

Not yet implemented:

- Symbolic pointer/buffer cases and `encoded_memory_effects`.
- A native runner, process/signal isolation, dynamic symbol registry, ISA
  detector, MXCSR/FPSCR/VSCR preflight, or build-manifest evidence collector.
- Cross-compilation and execution verification of the ppc64le translation unit.
  It is source-complete as an implementation boundary, but only a ppc64le
  toolchain and host can turn it into conformance evidence.
- General RFC 8785 JSON decoding for arbitrary case signatures.

Build and run on a development host:

```sh
cmake -S . -B build/native -DBUILD_TESTING=ON
cmake --build build/native
ctest --test-dir build/native --output-on-failure
```
