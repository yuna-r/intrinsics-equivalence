#include <emmintrin.h>

typedef __m128i i8x16;

i8x16 intel_add_i8x16(i8x16 a, i8x16 b)
{
    return _mm_add_epi8(a, b);
}

i8x16 intel_sub_i8x16(i8x16 a, i8x16 b)
{
    return _mm_sub_epi8(a, b);
}

i8x16 intel_adds_i8x16(i8x16 a, i8x16 b)
{
    return _mm_adds_epi8(a, b);
}

i8x16 intel_adds_u8x16(i8x16 a, i8x16 b)
{
    return _mm_adds_epu8(a, b);
}

i8x16 intel_subs_i8x16(i8x16 a, i8x16 b)
{
    return _mm_subs_epi8(a, b);
}

i8x16 intel_subs_u8x16(i8x16 a, i8x16 b)
{
    return _mm_subs_epu8(a, b);
}

i8x16 intel_cmpeq_i8x16(i8x16 a, i8x16 b)
{
    return _mm_cmpeq_epi8(a, b);
}

i8x16 intel_cmpgt_i8x16(i8x16 a, i8x16 b)
{
    return _mm_cmpgt_epi8(a, b);
}

i8x16 intel_avg_u8x16(i8x16 a, i8x16 b)
{
    return _mm_avg_epu8(a, b);
}

i8x16 intel_sad_u8x16(i8x16 a, i8x16 b)
{
    return _mm_sad_epu8(a, b);
}

i8x16 intel_min_u8x16(i8x16 a, i8x16 b)
{
    return _mm_min_epu8(a, b);
}

i8x16 intel_max_u8x16(i8x16 a, i8x16 b)
{
    return _mm_max_epu8(a, b);
}

i8x16 intel_slli_bytes_u8x16(i8x16 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_slli_si128(v, 0);
    case 1: return _mm_slli_si128(v, 1);
    case 7: return _mm_slli_si128(v, 7);
    case 15: return _mm_slli_si128(v, 15);
    case 16: return _mm_slli_si128(v, 16);
    case 255: return _mm_slli_si128(v, 255);
    default: return v;
    }
}

i8x16 intel_srli_bytes_u8x16(i8x16 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srli_si128(v, 0);
    case 1: return _mm_srli_si128(v, 1);
    case 7: return _mm_srli_si128(v, 7);
    case 15: return _mm_srli_si128(v, 15);
    case 16: return _mm_srli_si128(v, 16);
    case 255: return _mm_srli_si128(v, 255);
    default: return v;
    }
}

i8x16 intel_unpacklo_i8x16(i8x16 a, i8x16 b)
{
    return _mm_unpacklo_epi8(a, b);
}

i8x16 intel_unpackhi_i8x16(i8x16 a, i8x16 b)
{
    return _mm_unpackhi_epi8(a, b);
}

int intel_movemask_i8x16(i8x16 v)
{
    return _mm_movemask_epi8(v);
}
