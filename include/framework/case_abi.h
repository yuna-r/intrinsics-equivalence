#ifndef IOITF_FRAMEWORK_CASE_ABI_H
#define IOITF_FRAMEWORK_CASE_ABI_H

#include <stddef.h>
#include <stdint.h>

#if defined(__cplusplus)
extern "C" {
#define IOITF_STATIC_ASSERT(condition, message) static_assert(condition, message)
#else
#define IOITF_STATIC_ASSERT(condition, message) _Static_assert(condition, message)
#endif

typedef struct {
    const uint8_t* data;
    uint64_t size;
} ioitf_bytes;

typedef struct {
    uint32_t abi_version;
    uint32_t struct_size;
    ioitf_bytes encoded_arguments;
    uint32_t rounding_mode;
    uint32_t fp_mode;
} ioitf_input;

typedef struct {
    uint32_t abi_version;
    uint32_t struct_size;
    uint8_t* encoded_return_value;
    uint64_t return_capacity;
    uint64_t return_size;
    uint8_t* encoded_memory_effects;
    uint64_t effects_capacity;
    uint64_t effects_size;
    uint32_t normalized_fp_exceptions;
    uint32_t status;
} ioitf_output;

enum {
    IOITF_ABI_VERSION = 1,
    IOITF_ROUND_NEAREST_EVEN = 0,
    IOITF_ROUND_TOWARD_ZERO = 1,
    IOITF_ROUND_TOWARD_POSITIVE = 2,
    IOITF_ROUND_TOWARD_NEGATIVE = 3,
    IOITF_FP_MODE_IEEE = 0
};

enum {
    IOITF_OUTPUT_OK = 0,
    IOITF_OUTPUT_UNSUPPORTED = 1,
    IOITF_OUTPUT_INVALID_INPUT = 2,
    IOITF_OUTPUT_RUNTIME_ERROR = 3
};

enum {
    IOITF_CALL_OK = 0,
    IOITF_CALL_INVALID_ABI = 1,
    IOITF_CALL_OUTPUT_TOO_SMALL = 2,
    IOITF_CALL_RESOURCE_ERROR = 3
};

enum {
    IOITF_FP_INVALID = UINT32_C(1) << 0,
    IOITF_FP_DIVIDE_BY_ZERO = UINT32_C(1) << 1,
    IOITF_FP_OVERFLOW = UINT32_C(1) << 2,
    IOITF_FP_UNDERFLOW = UINT32_C(1) << 3,
    IOITF_FP_INEXACT = UINT32_C(1) << 4,
    IOITF_FP_ALL = (UINT32_C(1) << 5) - UINT32_C(1)
};

typedef int (*ioitf_case_fn)(const ioitf_input*, ioitf_output*);

/* ABI v1 is intentionally unavailable on 32-bit and LLP64 hosts. */
IOITF_STATIC_ASSERT(sizeof(void*) == 8, "IOITF ABI v1 requires 64-bit pointers");
IOITF_STATIC_ASSERT(sizeof(long) == 8, "IOITF ABI v1 requires LP64");
IOITF_STATIC_ASSERT(sizeof(uint64_t) == 8, "uint64_t must be 8 bytes");

IOITF_STATIC_ASSERT(sizeof(ioitf_bytes) == 16, "ioitf_bytes ABI size");
IOITF_STATIC_ASSERT(offsetof(ioitf_bytes, data) == 0, "ioitf_bytes.data ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_bytes, size) == 8, "ioitf_bytes.size ABI offset");

IOITF_STATIC_ASSERT(sizeof(ioitf_input) == 32, "ioitf_input ABI size");
IOITF_STATIC_ASSERT(offsetof(ioitf_input, abi_version) == 0,
                    "ioitf_input.abi_version ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_input, struct_size) == 4,
                    "ioitf_input.struct_size ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_input, encoded_arguments) == 8,
                    "ioitf_input.encoded_arguments ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_input, rounding_mode) == 24,
                    "ioitf_input.rounding_mode ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_input, fp_mode) == 28,
                    "ioitf_input.fp_mode ABI offset");

IOITF_STATIC_ASSERT(sizeof(ioitf_output) == 64, "ioitf_output ABI size");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, abi_version) == 0,
                    "ioitf_output.abi_version ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, struct_size) == 4,
                    "ioitf_output.struct_size ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, encoded_return_value) == 8,
                    "ioitf_output.encoded_return_value ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, return_capacity) == 16,
                    "ioitf_output.return_capacity ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, return_size) == 24,
                    "ioitf_output.return_size ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, encoded_memory_effects) == 32,
                    "ioitf_output.encoded_memory_effects ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, effects_capacity) == 40,
                    "ioitf_output.effects_capacity ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, effects_size) == 48,
                    "ioitf_output.effects_size ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, normalized_fp_exceptions) == 56,
                    "ioitf_output.normalized_fp_exceptions ABI offset");
IOITF_STATIC_ASSERT(offsetof(ioitf_output, status) == 60,
                    "ioitf_output.status ABI offset");

IOITF_STATIC_ASSERT(IOITF_ABI_VERSION == 1, "IOITF ABI version changed");
IOITF_STATIC_ASSERT(IOITF_OUTPUT_RUNTIME_ERROR == 3,
                    "IOITF output status numbering changed");
IOITF_STATIC_ASSERT(IOITF_CALL_RESOURCE_ERROR == 3,
                    "IOITF call status numbering changed");

#if defined(__cplusplus)
}
#endif

#undef IOITF_STATIC_ASSERT

#endif

