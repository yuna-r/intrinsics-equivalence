#include <emmintrin.h>

typedef __m128i i32x4;

i32x4 intel_add_i32x4(i32x4 a, i32x4 b)
{
    return _mm_add_epi32(a, b);
}

i32x4 intel_sub_i32x4(i32x4 a, i32x4 b)
{
    return _mm_sub_epi32(a, b);
}

i32x4 intel_and_i32x4(i32x4 a, i32x4 b)
{
    return _mm_and_si128(a, b);
}

i32x4 intel_or_i32x4(i32x4 a, i32x4 b)
{
    return _mm_or_si128(a, b);
}

i32x4 intel_xor_i32x4(i32x4 a, i32x4 b)
{
    return _mm_xor_si128(a, b);
}

i32x4 intel_andnot_i32x4(i32x4 a, i32x4 b)
{
    return _mm_andnot_si128(a, b);
}

i32x4 intel_cmpeq_i32x4(i32x4 a, i32x4 b)
{
    return _mm_cmpeq_epi32(a, b);
}

i32x4 intel_cmpgt_i32x4(i32x4 a, i32x4 b)
{
    return _mm_cmpgt_epi32(a, b);
}

i32x4 intel_slli_i32x4(i32x4 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_slli_epi32(v, 0);
    case 1: return _mm_slli_epi32(v, 1);
    case 15: return _mm_slli_epi32(v, 15);
    case 31: return _mm_slli_epi32(v, 31);
    case 32: return _mm_slli_epi32(v, 32);
    case 255: return _mm_slli_epi32(v, 255);
    default: return v;
    }
}

i32x4 intel_srli_i32x4(i32x4 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srli_epi32(v, 0);
    case 1: return _mm_srli_epi32(v, 1);
    case 15: return _mm_srli_epi32(v, 15);
    case 31: return _mm_srli_epi32(v, 31);
    case 32: return _mm_srli_epi32(v, 32);
    case 255: return _mm_srli_epi32(v, 255);
    default: return v;
    }
}

i32x4 intel_srai_i32x4(i32x4 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srai_epi32(v, 0);
    case 1: return _mm_srai_epi32(v, 1);
    case 15: return _mm_srai_epi32(v, 15);
    case 31: return _mm_srai_epi32(v, 31);
    case 32: return _mm_srai_epi32(v, 32);
    case 255: return _mm_srai_epi32(v, 255);
    default: return v;
    }
}

i32x4 intel_shuffle_i32x4(i32x4 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_shuffle_epi32(v, 0);
    case 1: return _mm_shuffle_epi32(v, 1);
    case 27: return _mm_shuffle_epi32(v, 27);
    case 255: return _mm_shuffle_epi32(v, 255);
    default: return v;
    }
}

i32x4 intel_unpacklo_i32x4(i32x4 a, i32x4 b)
{
    return _mm_unpacklo_epi32(a, b);
}

i32x4 intel_unpackhi_i32x4(i32x4 a, i32x4 b)
{
    return _mm_unpackhi_epi32(a, b);
}
