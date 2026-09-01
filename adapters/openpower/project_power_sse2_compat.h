#ifndef IOITF_PROJECT_POWER_SSE2_COMPAT_H
#define IOITF_PROJECT_POWER_SSE2_COMPAT_H

#include <altivec.h>

#if !defined(__powerpc64__) || !defined(__BYTE_ORDER__) || \
    !defined(__ORDER_LITTLE_ENDIAN__) || \
    __BYTE_ORDER__ != __ORDER_LITTLE_ENDIAN__
#error "POWER compatibility header requires ppc64le"
#endif

#define IOITF_POWER_SSE2_COMPAT 1

typedef __vector double __m128d;
typedef __vector unsigned int __m128i;

extern __inline__ __m128d
__attribute__((__gnu_inline__, __always_inline__, __artificial__))
_mm_add_pd(__m128d a, __m128d b)
{
    return (__m128d)(a + b);
}

extern __inline__ __m128d
__attribute__((__gnu_inline__, __always_inline__, __artificial__))
_mm_set1_pd(double value)
{
    return vec_splats(value);
}

static __inline__ __m128i
__attribute__((__always_inline__, __artificial__))
ioitf_power_mm_shuffle_epi32(__m128i value, unsigned int immediate)
{
    return (__m128i){
        value[(immediate >> 0) & 3U],
        value[(immediate >> 2) & 3U],
        value[(immediate >> 4) & 3U],
        value[(immediate >> 6) & 3U]
    };
}

#define _mm_shuffle_epi32(value, immediate) \
    ioitf_power_mm_shuffle_epi32((value), (unsigned int)(immediate))

#endif
