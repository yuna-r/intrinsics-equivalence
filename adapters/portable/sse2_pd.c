#include "f64x2_adapter.h"
#include "framework/example_cases.h"

#include <string.h>

#if !defined(IOITF_DEVELOPMENT_PORTABLE_ADAPTER) || \
    IOITF_DEVELOPMENT_PORTABLE_ADAPTER != 1
#error "portable adapter must be explicitly marked as a development fixture"
#endif

typedef struct {
    double a[2];
    double b[2];
    double result[2];
} portable_add_pd_context;

typedef struct {
    double value;
    double result[2];
} portable_set1_pd_context;

static void portable_prepare_mm_add_pd(void* opaque,
                                       const double a[2],
                                       const double b[2])
{
    portable_add_pd_context* context = (portable_add_pd_context*)opaque;
    memcpy(context->a, a, sizeof(context->a));
    memcpy(context->b, b, sizeof(context->b));
}

static void portable_invoke_mm_add_pd(void* opaque)
{
    portable_add_pd_context* context = (portable_add_pd_context*)opaque;
    context->result[0] = context->a[0] + context->b[0];
    context->result[1] = context->a[1] + context->b[1];
}

static void portable_extract_mm_add_pd(const void* opaque, double result[2])
{
    const portable_add_pd_context* context =
        (const portable_add_pd_context*)opaque;
    memcpy(result, context->result, sizeof(context->result));
}

static void portable_prepare_mm_set1_pd(void* opaque, double value)
{
    portable_set1_pd_context* context = (portable_set1_pd_context*)opaque;
    memcpy(&context->value, &value, sizeof(value));
}

static void portable_invoke_mm_set1_pd(void* opaque)
{
    portable_set1_pd_context* context = (portable_set1_pd_context*)opaque;
    context->result[0] = context->value;
    context->result[1] = context->value;
}

static void portable_extract_mm_set1_pd(const void* opaque, double result[2])
{
    const portable_set1_pd_context* context =
        (const portable_set1_pd_context*)opaque;
    memcpy(result, context->result, sizeof(context->result));
}

static const ioitf_add_pd_callbacks PORTABLE_ADD_PD_CALLBACKS = {
    portable_prepare_mm_add_pd,
    portable_invoke_mm_add_pd,
    portable_extract_mm_add_pd
};

static const ioitf_set1_pd_callbacks PORTABLE_SET1_PD_CALLBACKS = {
    portable_prepare_mm_set1_pd,
    portable_invoke_mm_set1_pd,
    portable_extract_mm_set1_pd
};

static void portable_call_mm_shuffle_epi32(const uint32_t lanes[4],
                                           uint8_t immediate,
                                           uint32_t result[4])
{
    unsigned lane;
    for (lane = 0; lane < 4; ++lane) {
        result[lane] = lanes[(immediate >> (2U * lane)) & 3U];
    }
}

int portable_mm_add_pd(const ioitf_input* input, ioitf_output* output)
{
    portable_add_pd_context context;
    return ioitf_execute_add_pd(input, output, &context,
                                &PORTABLE_ADD_PD_CALLBACKS, NULL);
}

int portable_mm_set1_pd(const ioitf_input* input, ioitf_output* output)
{
    portable_set1_pd_context context;
    return ioitf_execute_set1_pd(input, output, &context,
                                 &PORTABLE_SET1_PD_CALLBACKS, NULL);
}

int portable_mm_shuffle_epi32(const ioitf_input* input, ioitf_output* output)
{
    return ioitf_execute_shuffle_epi32(input, output,
                                       portable_call_mm_shuffle_epi32);
}
