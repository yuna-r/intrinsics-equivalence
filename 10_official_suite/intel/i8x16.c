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
