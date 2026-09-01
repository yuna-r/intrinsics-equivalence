#ifndef IOITF_FRAMEWORK_EXAMPLE_CASES_H
#define IOITF_FRAMEWORK_EXAMPLE_CASES_H

#include "framework/case_abi.h"

#if defined(__GNUC__) || defined(__clang__)
#define IOITF_CASE_API __attribute__((visibility("default")))
#else
#define IOITF_CASE_API
#endif

#if defined(__cplusplus)
extern "C" {
#endif

/* x86_64 SSE2 evidence-producing symbols. */
IOITF_CASE_API int intel_mm_add_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int intel_mm_set1_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int intel_mm_shuffle_epi32(const ioitf_input*, ioitf_output*);

/* ppc64le project-compatibility-layer evidence-producing symbols. */
IOITF_CASE_API int power_mm_add_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int power_mm_set1_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int power_mm_shuffle_epi32(const ioitf_input*, ioitf_output*);

/* Development-only scalar fixture; never valid as Intel/POWER evidence. */
IOITF_CASE_API int portable_mm_add_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int portable_mm_set1_pd(const ioitf_input*, ioitf_output*);
IOITF_CASE_API int portable_mm_shuffle_epi32(const ioitf_input*, ioitf_output*);

#if defined(__cplusplus)
}
#endif

#undef IOITF_CASE_API

#endif
