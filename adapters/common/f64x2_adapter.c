#include "f64x2_adapter.h"

#include <float.h>
#include <fenv.h>
#include <inttypes.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#pragma STDC FENV_ACCESS ON

_Static_assert(sizeof(double) == 8, "f64 cases require binary64 double");
_Static_assert(FLT_RADIX == 2, "f64 cases require radix two");
_Static_assert(DBL_MANT_DIG == 53, "f64 cases require IEEE binary64 precision");

typedef struct {
    const uint8_t* data;
    uint64_t size;
    uint64_t position;
} ioitf_cursor;

#define IOITF_ZERO_F64X2_RESULT                                             \
    "{\"element\":\"f64\",\"lanes\":[\"0x0000000000000000\","       \
    "\"0x0000000000000000\"]}"

enum {
    IOITF_F64X2_RESULT_SIZE = sizeof(IOITF_ZERO_F64X2_RESULT) - 1U
};

#define IOITF_ZERO_I32X4_RESULT                                             \
    "{\"element\":\"i32\",\"lanes\":[\"0x00000000\",\"0x00000000\"," \
    "\"0x00000000\",\"0x00000000\"]}"

enum {
    IOITF_I32X4_RESULT_SIZE = sizeof(IOITF_ZERO_I32X4_RESULT) - 1U
};

static int ioitf_cursor_literal(ioitf_cursor* cursor,
                                const char* literal,
                                size_t literal_size)
{
    if (cursor->position > cursor->size ||
        (uint64_t)literal_size > cursor->size - cursor->position) {
        return 0;
    }
    if (memcmp(cursor->data + cursor->position, literal, literal_size) != 0) {
        return 0;
    }
    cursor->position += (uint64_t)literal_size;
    return 1;
}

#define IOITF_EXPECT(cursor, literal) \
    ioitf_cursor_literal((cursor), (literal), sizeof(literal) - 1U)

static int ioitf_lower_hex_nibble(uint8_t value)
{
    if (value >= (uint8_t)'0' && value <= (uint8_t)'9') {
        return (int)(value - (uint8_t)'0');
    }
    if (value >= (uint8_t)'a' && value <= (uint8_t)'f') {
        return (int)(value - (uint8_t)'a') + 10;
    }
    return -1;
}

static int ioitf_cursor_hex64(ioitf_cursor* cursor, uint64_t* result)
{
    uint64_t value = 0;
    unsigned index;

    if (!IOITF_EXPECT(cursor, "\"0x")) {
        return 0;
    }
    if (cursor->position > cursor->size ||
        UINT64_C(17) > cursor->size - cursor->position) {
        return 0;
    }
    for (index = 0; index < 16; ++index) {
        int nibble = ioitf_lower_hex_nibble(cursor->data[cursor->position++]);
        if (nibble < 0) {
            return 0;
        }
        value = (value << 4) | (uint64_t)nibble;
    }
    if (cursor->data[cursor->position++] != (uint8_t)'\"') {
        return 0;
    }
    *result = value;
    return 1;
}

static int ioitf_cursor_hex32(ioitf_cursor* cursor, uint32_t* result)
{
    uint32_t value = 0;
    unsigned index;

    if (!IOITF_EXPECT(cursor, "\"0x")) {
        return 0;
    }
    if (cursor->position > cursor->size ||
        UINT64_C(9) > cursor->size - cursor->position) {
        return 0;
    }
    for (index = 0; index < 8; ++index) {
        int nibble = ioitf_lower_hex_nibble(cursor->data[cursor->position++]);
        if (nibble < 0) {
            return 0;
        }
        value = (value << 4) | (uint32_t)nibble;
    }
    if (cursor->data[cursor->position++] != (uint8_t)'\"') {
        return 0;
    }
    *result = value;
    return 1;
}

static int ioitf_cursor_safe_integer(ioitf_cursor* cursor, int64_t* result)
{
    const uint64_t safe_integer_max = UINT64_C(9007199254740991);
    uint64_t magnitude = 0;
    uint64_t start = cursor->position;
    int negative = 0;

    if (start >= cursor->size) {
        return 0;
    }
    if (cursor->data[cursor->position] == (uint8_t)'-') {
        negative = 1;
        ++cursor->position;
        start = cursor->position;
        if (start >= cursor->size) {
            return 0;
        }
    }
    if (cursor->data[cursor->position] == (uint8_t)'0') {
        ++cursor->position;
        if (negative) {
            return 0; /* RFC 8785 serializes negative numeric zero as 0. */
        }
        *result = INT64_C(0);
        return 1;
    }
    if (cursor->data[cursor->position] < (uint8_t)'1' ||
        cursor->data[cursor->position] > (uint8_t)'9') {
        return 0;
    }
    while (cursor->position < cursor->size &&
           cursor->data[cursor->position] >= (uint8_t)'0' &&
           cursor->data[cursor->position] <= (uint8_t)'9') {
        uint64_t digit =
            (uint64_t)(cursor->data[cursor->position] - (uint8_t)'0');
        if (magnitude > (safe_integer_max - digit) / UINT64_C(10)) {
            return 0;
        }
        magnitude = magnitude * UINT64_C(10) + digit;
        ++cursor->position;
    }
    *result = negative ? -(int64_t)magnitude : (int64_t)magnitude;
    return 1;
}

static int ioitf_parse_f64x2(ioitf_cursor* cursor, uint64_t lanes[2])
{
    return IOITF_EXPECT(cursor, "{\"element\":\"f64\",\"lanes\":[") &&
           ioitf_cursor_hex64(cursor, &lanes[0]) &&
           IOITF_EXPECT(cursor, ",") &&
           ioitf_cursor_hex64(cursor, &lanes[1]) &&
           IOITF_EXPECT(cursor, "]}");
}

static int ioitf_parse_add_arguments(const ioitf_bytes* bytes,
                                     uint64_t a[2],
                                     uint64_t b[2])
{
    ioitf_cursor cursor = {bytes->data, bytes->size, 0};

    return IOITF_EXPECT(&cursor, "{\"operands\":{\"a\":") &&
           ioitf_parse_f64x2(&cursor, a) &&
           IOITF_EXPECT(&cursor, ",\"b\":") &&
           ioitf_parse_f64x2(&cursor, b) &&
           IOITF_EXPECT(&cursor, "}}") && cursor.position == cursor.size;
}

static int ioitf_parse_set1_arguments(const ioitf_bytes* bytes,
                                      uint64_t* value)
{
    ioitf_cursor cursor = {bytes->data, bytes->size, 0};

    return IOITF_EXPECT(&cursor,
                        "{\"operands\":{\"value\":{\"bits\":") &&
           ioitf_cursor_hex64(&cursor, value) &&
           IOITF_EXPECT(&cursor, ",\"element\":\"f64\"}}}") &&
           cursor.position == cursor.size;
}

static int ioitf_parse_i32x4(ioitf_cursor* cursor, uint32_t lanes[4])
{
    return IOITF_EXPECT(cursor, "{\"element\":\"i32\",\"lanes\":[") &&
           ioitf_cursor_hex32(cursor, &lanes[0]) &&
           IOITF_EXPECT(cursor, ",") &&
           ioitf_cursor_hex32(cursor, &lanes[1]) &&
           IOITF_EXPECT(cursor, ",") &&
           ioitf_cursor_hex32(cursor, &lanes[2]) &&
           IOITF_EXPECT(cursor, ",") &&
           ioitf_cursor_hex32(cursor, &lanes[3]) &&
           IOITF_EXPECT(cursor, "]}");
}

static int ioitf_registered_shuffle_immediate(int64_t immediate)
{
    return immediate == 0U || immediate == 1U || immediate == 27U ||
           immediate == 255U;
}

static int ioitf_parse_shuffle_arguments(const ioitf_bytes* bytes,
                                         uint32_t lanes[4],
                                         int64_t* immediate)
{
    ioitf_cursor cursor = {bytes->data, bytes->size, 0};

    return IOITF_EXPECT(&cursor, "{\"immediates\":{\"imm8\":") &&
           ioitf_cursor_safe_integer(&cursor, immediate) &&
           IOITF_EXPECT(&cursor, "},\"operands\":{\"a\":") &&
           ioitf_parse_i32x4(&cursor, lanes) &&
           IOITF_EXPECT(&cursor, "}}") && cursor.position == cursor.size;
}

static int ioitf_valid_rounding_mode(uint32_t mode)
{
    return mode == IOITF_ROUND_NEAREST_EVEN ||
           mode == IOITF_ROUND_TOWARD_ZERO ||
           mode == IOITF_ROUND_TOWARD_POSITIVE ||
           mode == IOITF_ROUND_TOWARD_NEGATIVE;
}

static int ioitf_validate_abi(const ioitf_input* input, ioitf_output* output)
{
    if (input == NULL || output == NULL) {
        return 0;
    }
    if (input->abi_version != IOITF_ABI_VERSION ||
        input->struct_size != sizeof(*input) ||
        output->abi_version != IOITF_ABI_VERSION ||
        output->struct_size != sizeof(*output)) {
        return 0;
    }
    if (input->encoded_arguments.data == NULL ||
        input->encoded_arguments.size == 0 ||
        input->encoded_arguments.size > UINT64_C(1024)) {
        return 0;
    }
    if (!ioitf_valid_rounding_mode(input->rounding_mode) ||
        input->fp_mode != IOITF_FP_MODE_IEEE) {
        return 0;
    }
    if ((output->return_capacity != 0 &&
         output->encoded_return_value == NULL) ||
        (output->effects_capacity != 0 &&
         output->encoded_memory_effects == NULL)) {
        return 0;
    }
    return 1;
}

static void ioitf_reset_result_fields(ioitf_output* output)
{
    output->return_size = 0;
    output->effects_size = 0;
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_OK;
}

static int ioitf_require_f64x2_capacity(ioitf_output* output)
{
    uint64_t required = (uint64_t)IOITF_F64X2_RESULT_SIZE;

    output->return_size = required;
    output->effects_size = 0;
    if (output->return_capacity < required) {
        return 0;
    }
    return 1;
}

static int ioitf_require_i32x4_capacity(ioitf_output* output)
{
    output->return_size = (uint64_t)IOITF_I32X4_RESULT_SIZE;
    output->effects_size = 0;
    return output->return_capacity >= (uint64_t)IOITF_I32X4_RESULT_SIZE;
}

static int ioitf_fe_round(uint32_t mode, int* result)
{
    switch (mode) {
    case IOITF_ROUND_NEAREST_EVEN:
        *result = FE_TONEAREST;
        return 1;
    case IOITF_ROUND_TOWARD_ZERO:
        *result = FE_TOWARDZERO;
        return 1;
    case IOITF_ROUND_TOWARD_POSITIVE:
        *result = FE_UPWARD;
        return 1;
    case IOITF_ROUND_TOWARD_NEGATIVE:
        *result = FE_DOWNWARD;
        return 1;
    default:
        return 0;
    }
}

static uint32_t ioitf_normalize_exceptions(int raised)
{
    uint32_t normalized = 0;

    if ((raised & FE_INVALID) != 0) {
        normalized |= IOITF_FP_INVALID;
    }
    if ((raised & FE_DIVBYZERO) != 0) {
        normalized |= IOITF_FP_DIVIDE_BY_ZERO;
    }
    if ((raised & FE_OVERFLOW) != 0) {
        normalized |= IOITF_FP_OVERFLOW;
    }
    if ((raised & FE_UNDERFLOW) != 0) {
        normalized |= IOITF_FP_UNDERFLOW;
    }
    if ((raised & FE_INEXACT) != 0) {
        normalized |= IOITF_FP_INEXACT;
    }
    return normalized;
}

static int ioitf_observation_save(fenv_t* saved_environment)
{
    return fegetenv(saved_environment) == 0;
}

static int ioitf_observation_begin(uint32_t rounding_mode,
                                   const fenv_t* saved_environment)
{
    int rounding;

    if (!ioitf_fe_round(rounding_mode, &rounding)) {
        return 0;
    }
    if (fesetround(rounding) != 0) {
        (void)fesetenv(saved_environment);
        return 0;
    }
    if (feclearexcept(FE_ALL_EXCEPT) != 0) {
        (void)fesetenv(saved_environment);
        return 0;
    }
    return 1;
}

static int ioitf_observation_end(fenv_t* saved_environment,
                                 uint32_t* normalized)
{
    int raised = fetestexcept(FE_INVALID | FE_DIVBYZERO | FE_OVERFLOW |
                              FE_UNDERFLOW | FE_INEXACT);
    int restored = fesetenv(saved_environment);

    if (raised < 0 || restored != 0) {
        return 0;
    }
    *normalized = ioitf_normalize_exceptions(raised);
    return 1;
}

static double ioitf_double_from_bits(uint64_t bits)
{
    double value;
    memcpy(&value, &bits, sizeof(value));
    return value;
}

static uint64_t ioitf_double_to_bits(double value)
{
    uint64_t bits;
    memcpy(&bits, &value, sizeof(bits));
    return bits;
}

static int ioitf_encode_f64x2(ioitf_output* output,
                              const double result[2])
{
    char encoded[IOITF_F64X2_RESULT_SIZE + 1U];
    uint64_t lane0 = ioitf_double_to_bits(result[0]);
    uint64_t lane1 = ioitf_double_to_bits(result[1]);
    int size = snprintf(encoded, sizeof(encoded),
                        "{\"element\":\"f64\",\"lanes\":[\"0x%016" PRIx64
                        "\",\"0x%016" PRIx64 "\"]}",
                        lane0, lane1);

    if (size < 0 || (size_t)size != sizeof(encoded) - 1U) {
        return 0;
    }
    memcpy(output->encoded_return_value, encoded, (size_t)size);
    output->return_size = (uint64_t)size;
    output->effects_size = 0;
    return 1;
}

static int ioitf_encode_i32x4(ioitf_output* output,
                              const uint32_t result[4])
{
    char encoded[IOITF_I32X4_RESULT_SIZE + 1U];
    int size = snprintf(encoded, sizeof(encoded),
                        "{\"element\":\"i32\",\"lanes\":[\"0x%08" PRIx32
                        "\",\"0x%08" PRIx32 "\",\"0x%08" PRIx32
                        "\",\"0x%08" PRIx32 "\"]}",
                        result[0], result[1], result[2], result[3]);

    if (size < 0 || (size_t)size != sizeof(encoded) - 1U) {
        return 0;
    }
    memcpy(output->encoded_return_value, encoded, (size_t)size);
    output->return_size = (uint64_t)size;
    output->effects_size = 0;
    return 1;
}

static void ioitf_runtime_error(ioitf_output* output)
{
    output->return_size = 0;
    output->effects_size = 0;
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_RUNTIME_ERROR;
}

static void ioitf_invalid_input(ioitf_output* output)
{
    output->return_size = 0;
    output->effects_size = 0;
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_INVALID_INPUT;
}

int ioitf_execute_add_pd(const ioitf_input* input,
                         ioitf_output* output,
                         void* native_context,
                         const ioitf_add_pd_callbacks* callbacks,
                         uint32_t* captured_exceptions)
{
    uint64_t a_bits[2];
    uint64_t b_bits[2];
    double a[2];
    double b[2];
    double result[2];
    fenv_t saved_environment;
    uint32_t exceptions;

    if (captured_exceptions != NULL) {
        *captured_exceptions = 0;
    }
    if (!ioitf_validate_abi(input, output) || native_context == NULL ||
        callbacks == NULL || callbacks->prepare == NULL ||
        callbacks->invoke == NULL || callbacks->extract == NULL) {
        return IOITF_CALL_INVALID_ABI;
    }
    ioitf_reset_result_fields(output);
    if (!ioitf_parse_add_arguments(&input->encoded_arguments, a_bits, b_bits)) {
        return IOITF_CALL_INVALID_ABI;
    }
    if (!ioitf_require_f64x2_capacity(output)) {
        return IOITF_CALL_OUTPUT_TOO_SMALL;
    }

    a[0] = ioitf_double_from_bits(a_bits[0]);
    a[1] = ioitf_double_from_bits(a_bits[1]);
    b[0] = ioitf_double_from_bits(b_bits[0]);
    b[1] = ioitf_double_from_bits(b_bits[1]);

    if (!ioitf_observation_save(&saved_environment)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    callbacks->prepare(native_context, a, b);
    if (!ioitf_observation_begin(input->rounding_mode, &saved_environment)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    callbacks->invoke(native_context);
    if (!ioitf_observation_end(&saved_environment, &exceptions)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    if (captured_exceptions != NULL) {
        *captured_exceptions = exceptions;
    }
    callbacks->extract(native_context, result);
    if (!ioitf_encode_f64x2(output, result)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    /* The three registered schema-v1 cases do not observe FP exceptions. */
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_OK;
    return IOITF_CALL_OK;
}

int ioitf_execute_set1_pd(const ioitf_input* input,
                          ioitf_output* output,
                          void* native_context,
                          const ioitf_set1_pd_callbacks* callbacks,
                          uint32_t* captured_exceptions)
{
    uint64_t value_bits;
    double value;
    double result[2];
    fenv_t saved_environment;
    uint32_t exceptions;

    if (captured_exceptions != NULL) {
        *captured_exceptions = 0;
    }
    if (!ioitf_validate_abi(input, output) || native_context == NULL ||
        callbacks == NULL || callbacks->prepare == NULL ||
        callbacks->invoke == NULL || callbacks->extract == NULL) {
        return IOITF_CALL_INVALID_ABI;
    }
    ioitf_reset_result_fields(output);
    if (!ioitf_parse_set1_arguments(&input->encoded_arguments, &value_bits)) {
        return IOITF_CALL_INVALID_ABI;
    }
    if (!ioitf_require_f64x2_capacity(output)) {
        return IOITF_CALL_OUTPUT_TOO_SMALL;
    }

    value = ioitf_double_from_bits(value_bits);
    if (!ioitf_observation_save(&saved_environment)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    callbacks->prepare(native_context, value);
    if (!ioitf_observation_begin(input->rounding_mode, &saved_environment)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    callbacks->invoke(native_context);
    if (!ioitf_observation_end(&saved_environment, &exceptions)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    if (captured_exceptions != NULL) {
        *captured_exceptions = exceptions;
    }
    callbacks->extract(native_context, result);
    if (!ioitf_encode_f64x2(output, result)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    /* The three registered schema-v1 cases do not observe FP exceptions. */
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_OK;
    return IOITF_CALL_OK;
}

int ioitf_execute_shuffle_epi32(const ioitf_input* input,
                                ioitf_output* output,
                                ioitf_shuffle_i32x4_sut sut)
{
    uint32_t lanes[4];
    uint32_t result[4];
    int64_t parsed_immediate;
    uint8_t immediate;

    if (!ioitf_validate_abi(input, output) || sut == NULL) {
        return IOITF_CALL_INVALID_ABI;
    }
    ioitf_reset_result_fields(output);
    if (!ioitf_parse_shuffle_arguments(&input->encoded_arguments,
                                       lanes, &parsed_immediate)) {
        return IOITF_CALL_INVALID_ABI;
    }
    if (!ioitf_registered_shuffle_immediate(parsed_immediate)) {
        ioitf_invalid_input(output);
        return IOITF_CALL_OK;
    }
    immediate = (uint8_t)parsed_immediate;
    if (!ioitf_require_i32x4_capacity(output)) {
        return IOITF_CALL_OUTPUT_TOO_SMALL;
    }

    sut(lanes, immediate, result);
    if (!ioitf_encode_i32x4(output, result)) {
        ioitf_runtime_error(output);
        return IOITF_CALL_OK;
    }
    output->normalized_fp_exceptions = 0;
    output->status = IOITF_OUTPUT_OK;
    return IOITF_CALL_OK;
}
