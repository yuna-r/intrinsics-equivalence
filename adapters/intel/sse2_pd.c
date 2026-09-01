#include "f64x2_adapter.h"
#include "framework/example_cases.h"

#include <emmintrin.h>

#if !defined(__x86_64__) && !defined(_M_X64)
#error "Intel SSE2 adapter must be compiled for x86_64"
#endif

_Static_assert(sizeof(__m128d) == 16, "__m128d must be 128 bits");

typedef struct {
    __m128d a;
    __m128d b;
    __m128d result;
} intel_add_pd_context;

typedef struct {
    double value;
    __m128d result;
} intel_set1_pd_context;

static void intel_prepare_mm_add_pd(void* opaque,
                                    const double a[2],
                                    const double b[2])
{
    intel_add_pd_context* context = (intel_add_pd_context*)opaque;
    context->a = _mm_set_pd(a[1], a[0]);
    context->b = _mm_set_pd(b[1], b[0]);
}

static void intel_invoke_mm_add_pd(void* opaque)
{
    intel_add_pd_context* context = (intel_add_pd_context*)opaque;
    context->result = _mm_add_pd(context->a, context->b);
}

static void intel_extract_mm_add_pd(const void* opaque, double result[2])
{
    const intel_add_pd_context* context = (const intel_add_pd_context*)opaque;
    _mm_storeu_pd(result, context->result);
}

static void intel_prepare_mm_set1_pd(void* opaque, double value)
{
    intel_set1_pd_context* context = (intel_set1_pd_context*)opaque;
    context->value = value;
}

static void intel_invoke_mm_set1_pd(void* opaque)
{
    intel_set1_pd_context* context = (intel_set1_pd_context*)opaque;
    context->result = _mm_set1_pd(context->value);
}

static void intel_extract_mm_set1_pd(const void* opaque, double result[2])
{
    const intel_set1_pd_context* context = (const intel_set1_pd_context*)opaque;
    _mm_storeu_pd(result, context->result);
}

static const ioitf_add_pd_callbacks INTEL_ADD_PD_CALLBACKS = {
    intel_prepare_mm_add_pd,
    intel_invoke_mm_add_pd,
    intel_extract_mm_add_pd
};

static const ioitf_set1_pd_callbacks INTEL_SET1_PD_CALLBACKS = {
    intel_prepare_mm_set1_pd,
    intel_invoke_mm_set1_pd,
    intel_extract_mm_set1_pd
};

static void intel_store_i32x4(uint32_t result[4], __m128i value)
{
    _mm_storeu_si128((__m128i*)(void*)result, value);
}

static void intel_call_mm_shuffle_epi32(const uint32_t lanes[4],
                                        uint8_t immediate,
                                        uint32_t result[4])
{
    __m128i input = _mm_loadu_si128((const __m128i*)(const void*)lanes);
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
        /* The case-specific decoder rejects this before the SUT call. */
        shuffled = input;
        break;
    }
    intel_store_i32x4(result, shuffled);
}

int intel_mm_add_pd(const ioitf_input* input, ioitf_output* output)
{
    intel_add_pd_context context;
    return ioitf_execute_add_pd(input, output, &context,
                                &INTEL_ADD_PD_CALLBACKS, NULL);
}

int intel_mm_set1_pd(const ioitf_input* input, ioitf_output* output)
{
    intel_set1_pd_context context;
    return ioitf_execute_set1_pd(input, output, &context,
                                 &INTEL_SET1_PD_CALLBACKS, NULL);
}

int intel_mm_shuffle_epi32(const ioitf_input* input, ioitf_output* output)
{
    return ioitf_execute_shuffle_epi32(input, output,
                                       intel_call_mm_shuffle_epi32);
}
