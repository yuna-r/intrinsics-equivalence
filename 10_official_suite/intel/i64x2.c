#include <emmintrin.h>

typedef __m128i i64x2;

i64x2 intel_add_i64x2(i64x2 a, i64x2 b)
{
    return _mm_add_epi64(a, b);
}

i64x2 intel_sub_i64x2(i64x2 a, i64x2 b)
{
    return _mm_sub_epi64(a, b);
}

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

i64x2 intel_unpacklo_i64x2(i64x2 a, i64x2 b)
{
    return _mm_unpacklo_epi64(a, b);
}

i64x2 intel_unpackhi_i64x2(i64x2 a, i64x2 b)
{
    return _mm_unpackhi_epi64(a, b);
}

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
