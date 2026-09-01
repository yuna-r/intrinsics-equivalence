#ifndef IOITF_ADAPTERS_COMMON_F64X2_ADAPTER_H
#define IOITF_ADAPTERS_COMMON_F64X2_ADAPTER_H

#include "framework/case_abi.h"

#if defined(__GNUC__) || defined(__clang__)
#define IOITF_INTERNAL __attribute__((visibility("hidden")))
#else
#define IOITF_INTERNAL
#endif

typedef void (*ioitf_shuffle_i32x4_sut)(const uint32_t[4],
                                        uint8_t,
                                        uint32_t[4]);

typedef struct {
    void (*prepare)(void*, const double[2], const double[2]);
    void (*invoke)(void*);
    void (*extract)(const void*, double[2]);
} ioitf_add_pd_callbacks;

typedef struct {
    void (*prepare)(void*, double);
    void (*invoke)(void*);
    void (*extract)(const void*, double[2]);
} ioitf_set1_pd_callbacks;

IOITF_INTERNAL int ioitf_execute_add_pd(const ioitf_input* input,
                                        ioitf_output* output,
                                        void* native_context,
                                        const ioitf_add_pd_callbacks* callbacks,
                                        uint32_t* captured_exceptions);
IOITF_INTERNAL int ioitf_execute_set1_pd(const ioitf_input* input,
                                         ioitf_output* output,
                                         void* native_context,
                                         const ioitf_set1_pd_callbacks* callbacks,
                                         uint32_t* captured_exceptions);
IOITF_INTERNAL int ioitf_execute_shuffle_epi32(
    const ioitf_input* input,
    ioitf_output* output,
    ioitf_shuffle_i32x4_sut sut);

#undef IOITF_INTERNAL

#endif
