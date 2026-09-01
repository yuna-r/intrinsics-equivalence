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

i16x8 intel_mullo_i16x8(i16x8 a, i16x8 b)
{
    return _mm_mullo_epi16(a, b);
}

i16x8 intel_mulhi_i16x8(i16x8 a, i16x8 b)
{
    return _mm_mulhi_epi16(a, b);
}

i16x8 intel_mulhi_u16x8(i16x8 a, i16x8 b)
{
    return _mm_mulhi_epu16(a, b);
}

i16x8 intel_madd_i16x8(i16x8 a, i16x8 b)
{
    return _mm_madd_epi16(a, b);
}

i16x8 intel_avg_u16x8(i16x8 a, i16x8 b)
{
    return _mm_avg_epu16(a, b);
}

i16x8 intel_min_i16x8(i16x8 a, i16x8 b)
{
    return _mm_min_epi16(a, b);
}

i16x8 intel_max_i16x8(i16x8 a, i16x8 b)
{
    return _mm_max_epi16(a, b);
}

i16x8 intel_slli_i16x8(i16x8 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_slli_epi16(v, 0);
    case 1: return _mm_slli_epi16(v, 1);
    case 7: return _mm_slli_epi16(v, 7);
    case 15: return _mm_slli_epi16(v, 15);
    case 16: return _mm_slli_epi16(v, 16);
    case 255: return _mm_slli_epi16(v, 255);
    default: return v;
    }
}

i16x8 intel_srli_i16x8(i16x8 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srli_epi16(v, 0);
    case 1: return _mm_srli_epi16(v, 1);
    case 7: return _mm_srli_epi16(v, 7);
    case 15: return _mm_srli_epi16(v, 15);
    case 16: return _mm_srli_epi16(v, 16);
    case 255: return _mm_srli_epi16(v, 255);
    default: return v;
    }
}

i16x8 intel_srai_i16x8(i16x8 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_srai_epi16(v, 0);
    case 1: return _mm_srai_epi16(v, 1);
    case 7: return _mm_srai_epi16(v, 7);
    case 15: return _mm_srai_epi16(v, 15);
    case 16: return _mm_srai_epi16(v, 16);
    case 255: return _mm_srai_epi16(v, 255);
    default: return v;
    }
}

i16x8 intel_unpacklo_i16x8(i16x8 a, i16x8 b)
{
    return _mm_unpacklo_epi16(a, b);
}

i16x8 intel_unpackhi_i16x8(i16x8 a, i16x8 b)
{
    return _mm_unpackhi_epi16(a, b);
}

i16x8 intel_packs_i16x8(i16x8 a, i16x8 b)
{
    return _mm_packs_epi16(a, b);
}

i16x8 intel_packus_i16x8(i16x8 a, i16x8 b)
{
    return _mm_packus_epi16(a, b);
}

i16x8 intel_shufflelo_i16x8(i16x8 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_shufflelo_epi16(v, 0);
    case 1: return _mm_shufflelo_epi16(v, 1);
    case 27: return _mm_shufflelo_epi16(v, 27);
    case 228: return _mm_shufflelo_epi16(v, 228);
    case 255: return _mm_shufflelo_epi16(v, 255);
    default: return v;
    }
}

i16x8 intel_shufflehi_i16x8(i16x8 v, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_shufflehi_epi16(v, 0);
    case 1: return _mm_shufflehi_epi16(v, 1);
    case 27: return _mm_shufflehi_epi16(v, 27);
    case 228: return _mm_shufflehi_epi16(v, 228);
    case 255: return _mm_shufflehi_epi16(v, 255);
    default: return v;
    }
}
