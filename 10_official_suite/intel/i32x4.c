#include <emmintrin.h>

typedef __m128i example_i32x4;

example_i32x4 intel_example_add_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_add_epi32(a, b);
}

example_i32x4 intel_example_sub_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_sub_epi32(a, b);
}

example_i32x4 intel_example_and_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_and_si128(a, b);
}

example_i32x4 intel_example_or_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_or_si128(a, b);
}

example_i32x4 intel_example_xor_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_xor_si128(a, b);
}

example_i32x4 intel_example_andnot_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_andnot_si128(a, b);
}

example_i32x4 intel_example_cmpeq_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_cmpeq_epi32(a, b);
}

example_i32x4 intel_example_cmpgt_i32x4(example_i32x4 a, example_i32x4 b)
{
    return _mm_cmpgt_epi32(a, b);
}

example_i32x4 intel_example_slli_i32x4(example_i32x4 value,
                                       unsigned int immediate)
{
    switch (immediate) {
    case 0: return _mm_slli_epi32(value, 0);
    case 1: return _mm_slli_epi32(value, 1);
    case 15: return _mm_slli_epi32(value, 15);
    case 31: return _mm_slli_epi32(value, 31);
    case 32: return _mm_slli_epi32(value, 32);
    case 255: return _mm_slli_epi32(value, 255);
    default: return value;
    }
}

example_i32x4 intel_example_srli_i32x4(example_i32x4 value,
                                       unsigned int immediate)
{
    switch (immediate) {
    case 0: return _mm_srli_epi32(value, 0);
    case 1: return _mm_srli_epi32(value, 1);
    case 15: return _mm_srli_epi32(value, 15);
    case 31: return _mm_srli_epi32(value, 31);
    case 32: return _mm_srli_epi32(value, 32);
    case 255: return _mm_srli_epi32(value, 255);
    default: return value;
    }
}

example_i32x4 intel_example_srai_i32x4(example_i32x4 value,
                                       unsigned int immediate)
{
    switch (immediate) {
    case 0: return _mm_srai_epi32(value, 0);
    case 1: return _mm_srai_epi32(value, 1);
    case 15: return _mm_srai_epi32(value, 15);
    case 31: return _mm_srai_epi32(value, 31);
    case 32: return _mm_srai_epi32(value, 32);
    case 255: return _mm_srai_epi32(value, 255);
    default: return value;
    }
}

example_i32x4 intel_example_shuffle_i32x4(example_i32x4 value,
                                          unsigned int immediate)
{
    switch (immediate) {
    case 0: return _mm_shuffle_epi32(value, 0);
    case 1: return _mm_shuffle_epi32(value, 1);
    case 27: return _mm_shuffle_epi32(value, 27);
    case 255: return _mm_shuffle_epi32(value, 255);
    default: return value;
    }
}

example_i32x4 intel_example_unpacklo_i32x4(example_i32x4 a,
                                           example_i32x4 b)
{
    return _mm_unpacklo_epi32(a, b);
}

example_i32x4 intel_example_unpackhi_i32x4(example_i32x4 a,
                                           example_i32x4 b)
{
    return _mm_unpackhi_epi32(a, b);
}
