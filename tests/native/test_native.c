#include "framework/case_abi.h"
#include "framework/example_cases.h"
#include "f64x2_adapter.h"

#include <fenv.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int failures;
static int capacity_probe_shuffle_calls;

typedef struct {
    double a[2];
    double b[2];
    double result[2];
    unsigned prepare_calls;
    unsigned invoke_calls;
    unsigned extract_calls;
    const uint32_t* captured_address;
    uint32_t captured_seen_during_extract;
    int raise_invalid_during_prepare;
    int raise_overflow_during_extract;
} counting_add_context;

#define CHECK(condition)                                                        \
    do {                                                                        \
        if (!(condition)) {                                                     \
            fprintf(stderr, "%s:%d: check failed: %s\n",                     \
                    __FILE__, __LINE__, #condition);                            \
            ++failures;                                                        \
        }                                                                       \
    } while (0)

static const char ADD_ARGUMENTS[] =
    "{\"operands\":{\"a\":{\"element\":\"f64\",\"lanes\":["
    "\"0x3ff0000000000000\",\"0x4024000000000000\"]},\"b\":{"
    "\"element\":\"f64\",\"lanes\":[\"0x4000000000000000\","
    "\"0x4034000000000000\"]}}}";

static const char ADD_EXPECTED[] =
    "{\"element\":\"f64\",\"lanes\":[\"0x4008000000000000\","
    "\"0x403e000000000000\"]}";

static const char SET1_NEGATIVE_ZERO_ARGUMENTS[] =
    "{\"operands\":{\"value\":{\"bits\":\"0x8000000000000000\","
    "\"element\":\"f64\"}}}";

static const char SET1_NEGATIVE_ZERO_EXPECTED[] =
    "{\"element\":\"f64\",\"lanes\":[\"0x8000000000000000\","
    "\"0x8000000000000000\"]}";

static const char SET1_SIGNALING_NAN_ARGUMENTS[] =
    "{\"operands\":{\"value\":{\"bits\":\"0x7ff0000000000001\","
    "\"element\":\"f64\"}}}";

static const char SET1_SIGNALING_NAN_EXPECTED[] =
    "{\"element\":\"f64\",\"lanes\":[\"0x7ff0000000000001\","
    "\"0x7ff0000000000001\"]}";

static const char ROUNDING_ARGUMENTS[] =
    "{\"operands\":{\"a\":{\"element\":\"f64\",\"lanes\":["
    "\"0x3ff0000000000000\",\"0x3ff0000000000000\"]},\"b\":{"
    "\"element\":\"f64\",\"lanes\":[\"0x3ca8000000000000\","
    "\"0x3ca8000000000000\"]}}}";

static const char ROUND_NEAREST_EXPECTED[] =
    "{\"element\":\"f64\",\"lanes\":[\"0x3ff0000000000001\","
    "\"0x3ff0000000000001\"]}";

static const char ROUND_ZERO_EXPECTED[] =
    "{\"element\":\"f64\",\"lanes\":[\"0x3ff0000000000000\","
    "\"0x3ff0000000000000\"]}";

#define SHUFFLE_ARGUMENTS_PREFIX "{\"immediates\":{\"imm8\":"
#define SHUFFLE_ARGUMENTS_SUFFIX                                             \
    "},\"operands\":{\"a\":{\"element\":\"i32\",\"lanes\":["       \
    "\"0x01234567\",\"0x89abcdef\",\"0xfedcba98\",\"0x76543210\"]}}}"

static const char SHUFFLE_0_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "0" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_1_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "1" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_27_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "27" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_255_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "255" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_UNREGISTERED_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "2" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_U8_OVERFLOW_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "256" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_NEGATIVE_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "-1" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_NONCANONICAL_IMMEDIATE_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "02" SHUFFLE_ARGUMENTS_SUFFIX;
static const char SHUFFLE_NEGATIVE_ZERO_ARGUMENTS[] =
    SHUFFLE_ARGUMENTS_PREFIX "-0" SHUFFLE_ARGUMENTS_SUFFIX;

static const char SHUFFLE_0_EXPECTED[] =
    "{\"element\":\"i32\",\"lanes\":[\"0x01234567\",\"0x01234567\","
    "\"0x01234567\",\"0x01234567\"]}";
static const char SHUFFLE_1_EXPECTED[] =
    "{\"element\":\"i32\",\"lanes\":[\"0x89abcdef\",\"0x01234567\","
    "\"0x01234567\",\"0x01234567\"]}";
static const char SHUFFLE_27_EXPECTED[] =
    "{\"element\":\"i32\",\"lanes\":[\"0x76543210\",\"0xfedcba98\","
    "\"0x89abcdef\",\"0x01234567\"]}";
static const char SHUFFLE_255_EXPECTED[] =
    "{\"element\":\"i32\",\"lanes\":[\"0x76543210\",\"0x76543210\","
    "\"0x76543210\",\"0x76543210\"]}";

static ioitf_input make_input(const char* arguments, uint32_t rounding_mode)
{
    ioitf_input input;
    memset(&input, 0, sizeof(input));
    input.abi_version = IOITF_ABI_VERSION;
    input.struct_size = (uint32_t)sizeof(input);
    input.encoded_arguments.data = (const uint8_t*)arguments;
    input.encoded_arguments.size = (uint64_t)strlen(arguments);
    input.rounding_mode = rounding_mode;
    input.fp_mode = IOITF_FP_MODE_IEEE;
    return input;
}

static ioitf_output make_output(uint8_t* return_buffer, uint64_t capacity)
{
    ioitf_output output;
    memset(&output, 0, sizeof(output));
    output.abi_version = IOITF_ABI_VERSION;
    output.struct_size = (uint32_t)sizeof(output);
    output.encoded_return_value = return_buffer;
    output.return_capacity = capacity;
    return output;
}

static void check_case(ioitf_case_fn function,
                       const char* arguments,
                       uint32_t rounding_mode,
                       const char* expected,
                       uint32_t expected_exceptions)
{
    uint8_t buffer[256];
    ioitf_input input = make_input(arguments, rounding_mode);
    ioitf_output query = make_output(NULL, 0);
    ioitf_output output;
    int call_status;

    memset(buffer, 0xa5, sizeof(buffer));
    call_status = function(&input, &query);
    CHECK(call_status == IOITF_CALL_OUTPUT_TOO_SMALL);
    CHECK(query.return_size == strlen(expected));
    CHECK(query.effects_size == 0);

    output = make_output(buffer, query.return_size);
    call_status = function(&input, &output);
    CHECK(call_status == IOITF_CALL_OK);
    CHECK(output.status == IOITF_OUTPUT_OK);
    CHECK(output.return_size == strlen(expected));
    CHECK(output.effects_size == 0);
    CHECK(output.normalized_fp_exceptions == expected_exceptions);
    CHECK(memcmp(buffer, expected, strlen(expected)) == 0);
    CHECK(buffer[strlen(expected)] == 0xa5);
}

static void counting_add_prepare(void* opaque,
                                 const double a[2],
                                 const double b[2])
{
    counting_add_context* context = (counting_add_context*)opaque;
    ++context->prepare_calls;
    memcpy(context->a, a, sizeof(context->a));
    memcpy(context->b, b, sizeof(context->b));
    if (context->raise_invalid_during_prepare) {
        (void)feraiseexcept(FE_INVALID);
    }
}

static void counting_add_invoke(void* opaque)
{
    counting_add_context* context = (counting_add_context*)opaque;
    ++context->invoke_calls;
    context->result[0] = context->a[0] + context->b[0];
    context->result[1] = context->a[1] + context->b[1];
}

static void counting_add_extract(const void* opaque, double result[2])
{
    const counting_add_context* immutable =
        (const counting_add_context*)opaque;
    counting_add_context* context = (counting_add_context*)opaque;
    ++context->extract_calls;
    if (context->captured_address != NULL) {
        context->captured_seen_during_extract = *context->captured_address;
    }
    memcpy(result, immutable->result, sizeof(immutable->result));
    if (context->raise_overflow_during_extract) {
        (void)feraiseexcept(FE_OVERFLOW);
    }
}

static const ioitf_add_pd_callbacks COUNTING_ADD_CALLBACKS = {
    counting_add_prepare,
    counting_add_invoke,
    counting_add_extract
};

static void counting_shuffle_sut(const uint32_t lanes[4],
                                 uint8_t immediate,
                                 uint32_t result[4])
{
    unsigned lane;
    ++capacity_probe_shuffle_calls;
    for (lane = 0; lane < 4; ++lane) {
        result[lane] = lanes[(immediate >> (2U * lane)) & 3U];
    }
}

static void test_capacity_probe_does_not_execute_sut(void)
{
    uint8_t buffer[256];
    ioitf_input input = make_input(ADD_ARGUMENTS, IOITF_ROUND_NEAREST_EVEN);
    ioitf_output output = make_output(NULL, 0);
    counting_add_context add_context;
    uint32_t captured = UINT32_MAX;

    memset(&add_context, 0, sizeof(add_context));
    CHECK(ioitf_execute_add_pd(&input, &output, &add_context,
                               &COUNTING_ADD_CALLBACKS, &captured) ==
          IOITF_CALL_OUTPUT_TOO_SMALL);
    CHECK(add_context.prepare_calls == 0);
    CHECK(add_context.invoke_calls == 0);
    CHECK(add_context.extract_calls == 0);
    CHECK(captured == 0);

    output = make_output(buffer, output.return_size);
    CHECK(ioitf_execute_add_pd(&input, &output, &add_context,
                               &COUNTING_ADD_CALLBACKS, &captured) ==
          IOITF_CALL_OK);
    CHECK(add_context.prepare_calls == 1);
    CHECK(add_context.invoke_calls == 1);
    CHECK(add_context.extract_calls == 1);
    CHECK(captured == 0);

    input = make_input(SHUFFLE_27_ARGUMENTS, IOITF_ROUND_NEAREST_EVEN);
    output = make_output(NULL, 0);
    capacity_probe_shuffle_calls = 0;
    CHECK(ioitf_execute_shuffle_epi32(&input, &output,
                                      counting_shuffle_sut) ==
          IOITF_CALL_OUTPUT_TOO_SMALL);
    CHECK(capacity_probe_shuffle_calls == 0);

    output = make_output(buffer, output.return_size);
    CHECK(ioitf_execute_shuffle_epi32(&input, &output,
                                      counting_shuffle_sut) == IOITF_CALL_OK);
    CHECK(capacity_probe_shuffle_calls == 1);

    input = make_input(SHUFFLE_UNREGISTERED_ARGUMENTS,
                       IOITF_ROUND_NEAREST_EVEN);
    CHECK(ioitf_execute_shuffle_epi32(&input, &output,
                                      counting_shuffle_sut) ==
          IOITF_CALL_OK);
    CHECK(capacity_probe_shuffle_calls == 1);
    CHECK(output.status == IOITF_OUTPUT_INVALID_INPUT);
    CHECK(output.return_size == 0);
    CHECK(output.effects_size == 0);
    CHECK(output.normalized_fp_exceptions == 0);
}

static void test_internal_fp_observation_boundary(void)
{
    uint8_t buffer[256];
    ioitf_input input = make_input(ROUNDING_ARGUMENTS,
                                   IOITF_ROUND_NEAREST_EVEN);
    ioitf_output output = make_output(buffer, sizeof(buffer));
    counting_add_context context;
    uint32_t captured = 0;

    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
    memset(&context, 0, sizeof(context));
    context.captured_address = &captured;
    context.raise_invalid_during_prepare = 1;
    context.raise_overflow_during_extract = 1;
    CHECK(ioitf_execute_add_pd(&input, &output, &context,
                               &COUNTING_ADD_CALLBACKS, &captured) ==
          IOITF_CALL_OK);
    CHECK(context.prepare_calls == 1);
    CHECK(context.invoke_calls == 1);
    CHECK(context.extract_calls == 1);
    CHECK(captured == IOITF_FP_INEXACT);
    CHECK(context.captured_seen_during_extract == IOITF_FP_INEXACT);
    CHECK(output.normalized_fp_exceptions == 0);
    CHECK(output.return_size == strlen(ROUND_NEAREST_EXPECTED));
    CHECK(memcmp(buffer, ROUND_NEAREST_EXPECTED,
                 strlen(ROUND_NEAREST_EXPECTED)) == 0);
    CHECK((fetestexcept(FE_OVERFLOW) & FE_OVERFLOW) != 0);
    CHECK((fetestexcept(FE_INVALID) & FE_INVALID) == 0);
    CHECK(feclearexcept(FE_ALL_EXCEPT) == 0);
}

static void test_invalid_abi(void)
{
    uint8_t buffer[256];
    ioitf_input input = make_input(ADD_ARGUMENTS, IOITF_ROUND_NEAREST_EVEN);
    ioitf_output output = make_output(buffer, sizeof(buffer));
    char noncanonical[sizeof(ADD_ARGUMENTS) + 1U];

    CHECK(portable_mm_add_pd(NULL, &output) == IOITF_CALL_INVALID_ABI);
    CHECK(portable_mm_add_pd(&input, NULL) == IOITF_CALL_INVALID_ABI);

    input.abi_version = IOITF_ABI_VERSION + 1U;
    CHECK(portable_mm_add_pd(&input, &output) == IOITF_CALL_INVALID_ABI);
    input.abi_version = IOITF_ABI_VERSION;

    input.struct_size -= 1U;
    CHECK(portable_mm_add_pd(&input, &output) == IOITF_CALL_INVALID_ABI);
    input.struct_size = (uint32_t)sizeof(input);

    input.rounding_mode = 99;
    CHECK(portable_mm_add_pd(&input, &output) == IOITF_CALL_INVALID_ABI);
    input.rounding_mode = IOITF_ROUND_NEAREST_EVEN;

    output.return_capacity = 1;
    output.encoded_return_value = NULL;
    CHECK(portable_mm_add_pd(&input, &output) == IOITF_CALL_INVALID_ABI);
    output = make_output(buffer, sizeof(buffer));

    noncanonical[0] = ' ';
    memcpy(noncanonical + 1, ADD_ARGUMENTS, sizeof(ADD_ARGUMENTS));
    input.encoded_arguments.data = (const uint8_t*)noncanonical;
    input.encoded_arguments.size = strlen(ADD_ARGUMENTS) + 1U;
    CHECK(portable_mm_add_pd(&input, &output) == IOITF_CALL_INVALID_ABI);

    input = make_input(SHUFFLE_NONCANONICAL_IMMEDIATE_ARGUMENTS,
                       IOITF_ROUND_NEAREST_EVEN);
    CHECK(portable_mm_shuffle_epi32(&input, &output) ==
          IOITF_CALL_INVALID_ABI);

    input = make_input(SHUFFLE_NEGATIVE_ZERO_ARGUMENTS,
                       IOITF_ROUND_NEAREST_EVEN);
    CHECK(portable_mm_shuffle_epi32(&input, &output) ==
          IOITF_CALL_INVALID_ABI);
}

static void check_invalid_immediate(ioitf_case_fn function,
                                    const char* arguments)
{
    ioitf_input input = make_input(arguments, IOITF_ROUND_NEAREST_EVEN);
    ioitf_output output = make_output(NULL, 0);

    CHECK(function(&input, &output) == IOITF_CALL_OK);
    CHECK(output.status == IOITF_OUTPUT_INVALID_INPUT);
    CHECK(output.return_size == 0);
    CHECK(output.effects_size == 0);
    CHECK(output.normalized_fp_exceptions == 0);
}

static void test_invalid_input_status(void)
{
    check_invalid_immediate(portable_mm_shuffle_epi32,
                            SHUFFLE_UNREGISTERED_ARGUMENTS);
    check_invalid_immediate(portable_mm_shuffle_epi32,
                            SHUFFLE_U8_OVERFLOW_ARGUMENTS);
    check_invalid_immediate(portable_mm_shuffle_epi32,
                            SHUFFLE_NEGATIVE_ARGUMENTS);
#if defined(IOITF_TEST_INTEL_ADAPTER)
    check_invalid_immediate(intel_mm_shuffle_epi32,
                            SHUFFLE_UNREGISTERED_ARGUMENTS);
#elif defined(IOITF_TEST_OPENPOWER_ADAPTER)
    check_invalid_immediate(power_mm_shuffle_epi32,
                            SHUFFLE_UNREGISTERED_ARGUMENTS);
#endif
}

static void test_portable_cases(void)
{
    check_case(portable_mm_add_pd, ADD_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ADD_EXPECTED, 0);
    check_case(portable_mm_set1_pd, SET1_NEGATIVE_ZERO_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_NEGATIVE_ZERO_EXPECTED, 0);
    check_case(portable_mm_set1_pd, SET1_SIGNALING_NAN_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_SIGNALING_NAN_EXPECTED, 0);
    check_case(portable_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ROUND_NEAREST_EXPECTED,
               0);
    check_case(portable_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_TOWARD_ZERO, ROUND_ZERO_EXPECTED,
               0);
    check_case(portable_mm_shuffle_epi32, SHUFFLE_0_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_0_EXPECTED, 0);
    check_case(portable_mm_shuffle_epi32, SHUFFLE_1_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_1_EXPECTED, 0);
    check_case(portable_mm_shuffle_epi32, SHUFFLE_27_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_27_EXPECTED, 0);
    check_case(portable_mm_shuffle_epi32, SHUFFLE_255_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_255_EXPECTED, 0);
}

static void test_native_cases_when_available(void)
{
#if defined(IOITF_TEST_INTEL_ADAPTER)
    check_case(intel_mm_add_pd, ADD_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ADD_EXPECTED, 0);
    check_case(intel_mm_set1_pd, SET1_NEGATIVE_ZERO_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_NEGATIVE_ZERO_EXPECTED, 0);
    check_case(intel_mm_set1_pd, SET1_SIGNALING_NAN_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_SIGNALING_NAN_EXPECTED, 0);
    check_case(intel_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ROUND_NEAREST_EXPECTED,
               0);
    check_case(intel_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_TOWARD_ZERO, ROUND_ZERO_EXPECTED,
               0);
    check_case(intel_mm_shuffle_epi32, SHUFFLE_0_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_0_EXPECTED, 0);
    check_case(intel_mm_shuffle_epi32, SHUFFLE_1_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_1_EXPECTED, 0);
    check_case(intel_mm_shuffle_epi32, SHUFFLE_27_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_27_EXPECTED, 0);
    check_case(intel_mm_shuffle_epi32, SHUFFLE_255_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_255_EXPECTED, 0);
#elif defined(IOITF_TEST_OPENPOWER_ADAPTER)
    check_case(power_mm_add_pd, ADD_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ADD_EXPECTED, 0);
    check_case(power_mm_set1_pd, SET1_NEGATIVE_ZERO_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_NEGATIVE_ZERO_EXPECTED, 0);
    check_case(power_mm_set1_pd, SET1_SIGNALING_NAN_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SET1_SIGNALING_NAN_EXPECTED, 0);
    check_case(power_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, ROUND_NEAREST_EXPECTED,
               0);
    check_case(power_mm_add_pd, ROUNDING_ARGUMENTS,
               IOITF_ROUND_TOWARD_ZERO, ROUND_ZERO_EXPECTED,
               0);
    check_case(power_mm_shuffle_epi32, SHUFFLE_0_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_0_EXPECTED, 0);
    check_case(power_mm_shuffle_epi32, SHUFFLE_1_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_1_EXPECTED, 0);
    check_case(power_mm_shuffle_epi32, SHUFFLE_27_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_27_EXPECTED, 0);
    check_case(power_mm_shuffle_epi32, SHUFFLE_255_ARGUMENTS,
               IOITF_ROUND_NEAREST_EVEN, SHUFFLE_255_EXPECTED, 0);
#endif
}

int main(void)
{
    test_invalid_abi();
    test_invalid_input_status();
    test_capacity_probe_does_not_execute_sut();
    test_internal_fp_observation_boundary();
    test_portable_cases();
    test_native_cases_when_available();

    if (failures != 0) {
        fprintf(stderr, "%d native self-test check(s) failed\n", failures);
        return EXIT_FAILURE;
    }
    puts("native ABI and example adapter self-tests passed");
    return EXIT_SUCCESS;
}
