#include "f64x2_adapter.h"
#include "framework/example_cases.h"
#include "project_power_sse2_compat.h"

#if !defined(IOITF_POWER_SSE2_COMPAT) || IOITF_POWER_SSE2_COMPAT != 1
#error "project POWER SSE2 compatibility layer is required"
#endif

_Static_assert(sizeof(__m128d) == 16, "__m128d must be 128 bits");
_Static_assert(sizeof(__m128i) == 16, "__m128i must be 128 bits");
_Static_assert(sizeof(uint32_t) == sizeof(unsigned int),
               "POWER i32 lanes require 32-bit unsigned int");

static __m128d power_make_f64x2(const double lanes[2])
{
    __m128d result = vec_splats(0.0);
    result = vec_insert(lanes[0], result, 0);
    result = vec_insert(lanes[1], result, 1);
    return result;
}

static void power_extract_f64x2(__m128d value, double lanes[2])
{
    lanes[0] = vec_extract(value, 0);
    lanes[1] = vec_extract(value, 1);
}

typedef struct {
    __m128d a;
    __m128d b;
    __m128d result;
} power_add_pd_context;

typedef struct {
    double value;
    __m128d result;
} power_set1_pd_context;

static void power_prepare_mm_add_pd(void* opaque,
                                    const double a[2],
                                    const double b[2])
{
    power_add_pd_context* context = (power_add_pd_context*)opaque;
    context->a = power_make_f64x2(a);
    context->b = power_make_f64x2(b);
}

static void power_invoke_mm_add_pd(void* opaque)
{
    power_add_pd_context* context = (power_add_pd_context*)opaque;
    context->result = _mm_add_pd(context->a, context->b);
}

static void power_extract_mm_add_pd(const void* opaque, double result[2])
{
    const power_add_pd_context* context = (const power_add_pd_context*)opaque;
    power_extract_f64x2(context->result, result);
}

static void power_prepare_mm_set1_pd(void* opaque, double value)
{
    power_set1_pd_context* context = (power_set1_pd_context*)opaque;
    context->value = value;
}

static void power_invoke_mm_set1_pd(void* opaque)
{
    power_set1_pd_context* context = (power_set1_pd_context*)opaque;
    context->result = _mm_set1_pd(context->value);
}

static void power_extract_mm_set1_pd(const void* opaque, double result[2])
{
    const power_set1_pd_context* context = (const power_set1_pd_context*)opaque;
    power_extract_f64x2(context->result, result);
}

static const ioitf_add_pd_callbacks POWER_ADD_PD_CALLBACKS = {
    power_prepare_mm_add_pd,
    power_invoke_mm_add_pd,
    power_extract_mm_add_pd
};

static const ioitf_set1_pd_callbacks POWER_SET1_PD_CALLBACKS = {
    power_prepare_mm_set1_pd,
    power_invoke_mm_set1_pd,
    power_extract_mm_set1_pd
};

static __m128i power_make_i32x4(const uint32_t lanes[4])
{
    __m128i result = vec_splats(0U);
    result = vec_insert(lanes[0], result, 0);
    result = vec_insert(lanes[1], result, 1);
    result = vec_insert(lanes[2], result, 2);
    result = vec_insert(lanes[3], result, 3);
    return result;
}

static void power_extract_i32x4(__m128i value, uint32_t lanes[4])
{
    lanes[0] = vec_extract(value, 0);
    lanes[1] = vec_extract(value, 1);
    lanes[2] = vec_extract(value, 2);
    lanes[3] = vec_extract(value, 3);
}

static void power_call_mm_shuffle_epi32(const uint32_t lanes[4],
                                        uint8_t immediate,
                                        uint32_t result[4])
{
    __m128i input = power_make_i32x4(lanes);
    __m128i shuffled;

    switch (immediate) {
    case 0:
        shuffled = _mm_shuffle_epi32(input, 0);
        break;
    case 1:
        shuffled = _mm_shuffle_epi32(input, 1);
        break;
    case 27:
        shuffled = _mm_shuffle_epi32(input, 27);
        break;
    case 255:
        shuffled = _mm_shuffle_epi32(input, 255);
        break;
    default:
        shuffled = input;
        break;
    }
    power_extract_i32x4(shuffled, result);
}

int power_mm_add_pd(const ioitf_input* input, ioitf_output* output)
{
    power_add_pd_context context;
    return ioitf_execute_add_pd(input, output, &context,
                                &POWER_ADD_PD_CALLBACKS, NULL);
}

int power_mm_set1_pd(const ioitf_input* input, ioitf_output* output)
{
    power_set1_pd_context context;
    return ioitf_execute_set1_pd(input, output, &context,
                                 &POWER_SET1_PD_CALLBACKS, NULL);
}

int power_mm_shuffle_epi32(const ioitf_input* input, ioitf_output* output)
{
    return ioitf_execute_shuffle_epi32(input, output,
                                       power_call_mm_shuffle_epi32);
}
