#include "../shortcuts.h"
#include <emmintrin.h>

typedef __m128i i16x8;

i16x8 intel_set1_i16x8(short value)
{
    return _mm_set1_epi16(value);
}

IOITF_BINARY(i16x8, i16x8, intel_add_i16x8, _mm_add_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_sub_i16x8, _mm_sub_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_adds_i16x8, _mm_adds_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_adds_u16x8, _mm_adds_epu16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_subs_i16x8, _mm_subs_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_subs_u16x8, _mm_subs_epu16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_cmpeq_i16x8, _mm_cmpeq_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_cmpgt_i16x8, _mm_cmpgt_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_mullo_i16x8, _mm_mullo_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_mulhi_i16x8, _mm_mulhi_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_mulhi_u16x8, _mm_mulhi_epu16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_madd_i16x8, _mm_madd_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_avg_u16x8, _mm_avg_epu16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_min_i16x8, _mm_min_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_max_i16x8, _mm_max_epi16(a, b))

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

IOITF_BINARY(i16x8, i16x8, intel_unpacklo_i16x8, _mm_unpacklo_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_unpackhi_i16x8, _mm_unpackhi_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_packs_i16x8, _mm_packs_epi16(a, b))
IOITF_BINARY(i16x8, i16x8, intel_packus_i16x8, _mm_packus_epi16(a, b))

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

i16x8 intel_sll_i16x8(i16x8 a, __m128i count)
{
    return _mm_sll_epi16(a, count);
}

i16x8 intel_srl_i16x8(i16x8 a, __m128i count)
{
    return _mm_srl_epi16(a, count);
}

i16x8 intel_sra_i16x8(i16x8 a, __m128i count)
{
    return _mm_sra_epi16(a, count);
}

IOITF_BINARY(i16x8, i16x8, intel_cmplt_i16x8, _mm_cmplt_epi16(a, b))

i16x8 intel_set_i16x8(short lane7, short lane6, short lane5, short lane4,
                       short lane3, short lane2, short lane1, short lane0)
{
    return _mm_set_epi16(lane7, lane6, lane5, lane4,
                         lane3, lane2, lane1, lane0);
}

i16x8 intel_setr_i16x8(short lane0, short lane1, short lane2, short lane3,
                        short lane4, short lane5, short lane6, short lane7)
{
    return _mm_setr_epi16(lane0, lane1, lane2, lane3,
                          lane4, lane5, lane6, lane7);
}

unsigned intel_extract_i16x8(i16x8 a, unsigned imm)
{
    switch (imm) {
    case 0: return (unsigned)_mm_extract_epi16(a, 0);
    case 1: return (unsigned)_mm_extract_epi16(a, 1);
    case 2: return (unsigned)_mm_extract_epi16(a, 2);
    case 3: return (unsigned)_mm_extract_epi16(a, 3);
    case 4: return (unsigned)_mm_extract_epi16(a, 4);
    case 5: return (unsigned)_mm_extract_epi16(a, 5);
    case 6: return (unsigned)_mm_extract_epi16(a, 6);
    case 7: return (unsigned)_mm_extract_epi16(a, 7);
    default: return 0;
    }
}

i16x8 intel_insert_i16x8(i16x8 a, int value, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_insert_epi16(a, value, 0);
    case 1: return _mm_insert_epi16(a, value, 1);
    case 2: return _mm_insert_epi16(a, value, 2);
    case 3: return _mm_insert_epi16(a, value, 3);
    case 4: return _mm_insert_epi16(a, value, 4);
    case 5: return _mm_insert_epi16(a, value, 5);
    case 6: return _mm_insert_epi16(a, value, 6);
    case 7: return _mm_insert_epi16(a, value, 7);
    default: return a;
    }
}
