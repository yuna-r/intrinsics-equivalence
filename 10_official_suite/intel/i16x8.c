#include <emmintrin.h>

typedef __m128i i16x8;

i16x8 intel_add_i16x8(i16x8 a, i16x8 b)
{
    return _mm_add_epi16(a, b);
}

i16x8 intel_sub_i16x8(i16x8 a, i16x8 b)
{
    return _mm_sub_epi16(a, b);
}

i16x8 intel_adds_i16x8(i16x8 a, i16x8 b)
{
    return _mm_adds_epi16(a, b);
}

i16x8 intel_adds_u16x8(i16x8 a, i16x8 b)
{
    return _mm_adds_epu16(a, b);
}

i16x8 intel_subs_i16x8(i16x8 a, i16x8 b)
{
    return _mm_subs_epi16(a, b);
}

i16x8 intel_subs_u16x8(i16x8 a, i16x8 b)
{
    return _mm_subs_epu16(a, b);
}

i16x8 intel_cmpeq_i16x8(i16x8 a, i16x8 b)
{
    return _mm_cmpeq_epi16(a, b);
}

i16x8 intel_cmpgt_i16x8(i16x8 a, i16x8 b)
{
    return _mm_cmpgt_epi16(a, b);
}
