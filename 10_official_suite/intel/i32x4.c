#include "../shortcuts.h"
#include <emmintrin.h>

typedef __m128i i32x4;

IOITF_BINARY(i32x4, i32x4, intel_add_i32x4, _mm_add_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_sub_i32x4, _mm_sub_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_and_i32x4, _mm_and_si128(a, b))
IOITF_BINARY(i32x4, i32x4, intel_or_i32x4, _mm_or_si128(a, b))
IOITF_BINARY(i32x4, i32x4, intel_xor_i32x4, _mm_xor_si128(a, b))
IOITF_BINARY(i32x4, i32x4, intel_andnot_i32x4, _mm_andnot_si128(a, b))
IOITF_BINARY(i32x4, i32x4, intel_cmpeq_i32x4, _mm_cmpeq_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_cmpgt_i32x4, _mm_cmpgt_epi32(a, b))

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

IOITF_BINARY(i32x4, i32x4, intel_unpacklo_i32x4, _mm_unpacklo_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_unpackhi_i32x4, _mm_unpackhi_epi32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_mul_u32x4, _mm_mul_epu32(a, b))
IOITF_BINARY(i32x4, i32x4, intel_packs_i32x4, _mm_packs_epi32(a, b))

i32x4 intel_cvtsi32_i32x4(int value)
{
    return _mm_cvtsi32_si128(value);
}

i32x4 intel_set1_i32x4(int value)
{
    return _mm_set1_epi32(value);
}

i32x4 intel_sll_i32x4(i32x4 a, __m128i count)
{
    return _mm_sll_epi32(a, count);
}

i32x4 intel_srl_i32x4(i32x4 a, __m128i count)
{
    return _mm_srl_epi32(a, count);
}

i32x4 intel_sra_i32x4(i32x4 a, __m128i count)
{
    return _mm_sra_epi32(a, count);
}

IOITF_BINARY(i32x4, i32x4, intel_cmplt_i32x4, _mm_cmplt_epi32(a, b))
IOITF_UNARY(int, i32x4, intel_cvtsi128_i32x4, _mm_cvtsi128_si32(a))

i32x4 intel_set_i32x4(int lane3, int lane2, int lane1, int lane0)
{
    return _mm_set_epi32(lane3, lane2, lane1, lane0);
}

i32x4 intel_setr_i32x4(int lane0, int lane1, int lane2, int lane3)
{
    return _mm_setr_epi32(lane0, lane1, lane2, lane3);
}
