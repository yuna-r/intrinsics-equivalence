#include "../shortcuts.h"
#include <emmintrin.h>

typedef __m128i i64x2;

IOITF_BINARY(i64x2, i64x2, intel_add_i64x2, _mm_add_epi64(a, b))
IOITF_BINARY(i64x2, i64x2, intel_sub_i64x2, _mm_sub_epi64(a, b))

i64x2 intel_slli_i64x2(i64x2 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_slli_epi64(v, 0);
    case 1: return _mm_slli_epi64(v, 1);
    case 31: return _mm_slli_epi64(v, 31);
    case 63: return _mm_slli_epi64(v, 63);
    case 64: return _mm_slli_epi64(v, 64);
    case 255: return _mm_slli_epi64(v, 255);
    default: return v;
    }
}

i64x2 intel_srli_i64x2(i64x2 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srli_epi64(v, 0);
    case 1: return _mm_srli_epi64(v, 1);
    case 31: return _mm_srli_epi64(v, 31);
    case 63: return _mm_srli_epi64(v, 63);
    case 64: return _mm_srli_epi64(v, 64);
    case 255: return _mm_srli_epi64(v, 255);
    default: return v;
    }
}

IOITF_BINARY(i64x2, i64x2, intel_unpacklo_i64x2, _mm_unpacklo_epi64(a, b))
IOITF_BINARY(i64x2, i64x2, intel_unpackhi_i64x2, _mm_unpackhi_epi64(a, b))

i64x2 intel_move_i64x2(i64x2 value)
{
    return _mm_move_epi64(value);
}

i64x2 intel_cvtsi64_i64x2(long long value)
{
    return _mm_cvtsi64_si128(value);
}

i64x2 intel_set1_i64x2(long long value)
{
    return _mm_set1_epi64x(value);
}

i64x2 intel_sll_i64x2(i64x2 a, __m128i count)
{
    return _mm_sll_epi64(a, count);
}

i64x2 intel_srl_i64x2(i64x2 a, __m128i count)
{
    return _mm_srl_epi64(a, count);
}

IOITF_UNARY(long long, i64x2, intel_cvtsi128_i64x2, _mm_cvtsi128_si64(a))

i64x2 intel_set_i64x2(long long high, long long low)
{
    return _mm_set_epi64x(high, low);
}

i64x2 intel_loadl_i64x2(const void *source)
{
    return _mm_loadl_epi64((const __m128i *)source);
}

void intel_storel_i64x2(void *destination, i64x2 a)
{
    _mm_storel_epi64((__m128i *)destination, a);
}
