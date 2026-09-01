#include <altivec.h>

typedef __vector signed short i16x8;
typedef __vector unsigned short u16x8;
typedef __vector signed char i8x16;
typedef __vector unsigned char u8x16;
typedef __vector signed int i32x4;
typedef __vector unsigned int u32x4;
typedef __vector unsigned long long u64x2;

u16x8 power_add_i16x8(u16x8 a, u16x8 b)
{
    return a + b;
}

u16x8 power_sub_i16x8(u16x8 a, u16x8 b)
{
    return a - b;
}

u16x8 power_adds_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_adds((i16x8)a, (i16x8)b);
}

u16x8 power_adds_u16x8(u16x8 a, u16x8 b)
{
    return vec_adds(a, b);
}

u16x8 power_subs_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_subs((i16x8)a, (i16x8)b);
}

u16x8 power_subs_u16x8(u16x8 a, u16x8 b)
{
    return vec_subs(a, b);
}

u16x8 power_cmpeq_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_cmpeq(a, b);
}

u16x8 power_cmpgt_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_cmpgt((i16x8)a, (i16x8)b);
}

i16x8 power_mullo_i16x8(i16x8 a, i16x8 b)
{
    return (i16x8)((u16x8)a * (u16x8)b);
}

static unsigned short signed_mul_high(short a, short b)
{
    unsigned product = (unsigned)((int)a * (int)b);
    return (unsigned short)(product >> 16);
}

i16x8 power_mulhi_i16x8(i16x8 a, i16x8 b)
{
    return (i16x8)(u16x8){
        signed_mul_high(a[0], b[0]), signed_mul_high(a[1], b[1]),
        signed_mul_high(a[2], b[2]), signed_mul_high(a[3], b[3]),
        signed_mul_high(a[4], b[4]), signed_mul_high(a[5], b[5]),
        signed_mul_high(a[6], b[6]), signed_mul_high(a[7], b[7])};
}

static unsigned short unsigned_mul_high(unsigned short a, unsigned short b)
{
    return (unsigned short)(((unsigned)a * (unsigned)b) >> 16);
}

u16x8 power_mulhi_u16x8(u16x8 a, u16x8 b)
{
    return (u16x8){
        unsigned_mul_high(a[0], b[0]), unsigned_mul_high(a[1], b[1]),
        unsigned_mul_high(a[2], b[2]), unsigned_mul_high(a[3], b[3]),
        unsigned_mul_high(a[4], b[4]), unsigned_mul_high(a[5], b[5]),
        unsigned_mul_high(a[6], b[6]), unsigned_mul_high(a[7], b[7])};
}

i32x4 power_madd_i16x8(i16x8 a, i16x8 b)
{
    return vec_msum(a, b, vec_splats(0));
}

u16x8 power_avg_u16x8(u16x8 a, u16x8 b)
{
    return vec_avg(a, b);
}

i16x8 power_min_i16x8(i16x8 a, i16x8 b)
{
    return vec_min(a, b);
}

i16x8 power_max_i16x8(i16x8 a, i16x8 b)
{
    return vec_max(a, b);
}

i16x8 power_slli_i16x8(i16x8 v, unsigned imm)
{
    if (imm > 15U) {
        return (i16x8)vec_splats((unsigned short)0);
    }
    return (i16x8)vec_sl((u16x8)v, vec_splats((unsigned short)imm));
}

i16x8 power_srli_i16x8(i16x8 v, unsigned imm)
{
    if (imm > 15U) {
        return (i16x8)vec_splats((unsigned short)0);
    }
    return (i16x8)vec_sr((u16x8)v, vec_splats((unsigned short)imm));
}

i16x8 power_srai_i16x8(i16x8 v, unsigned imm)
{
    unsigned count = imm > 15U ? 15U : imm;
    return vec_sra(v, vec_splats((unsigned short)count));
}

i16x8 power_unpacklo_i16x8(i16x8 a, i16x8 b)
{
    return (i16x8){a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3]};
}

i16x8 power_unpackhi_i16x8(i16x8 a, i16x8 b)
{
    return (i16x8){a[4], b[4], a[5], b[5], a[6], b[6], a[7], b[7]};
}

i8x16 power_packs_i16x8(i16x8 a, i16x8 b)
{
    return vec_packs(a, b);
}

u8x16 power_packus_i16x8(i16x8 a, i16x8 b)
{
    return vec_packsu(a, b);
}

i16x8 power_shufflelo_i16x8(i16x8 v, unsigned imm)
{
    return (i16x8){v[(imm >> 0) & 3U], v[(imm >> 2) & 3U],
                    v[(imm >> 4) & 3U], v[(imm >> 6) & 3U],
                    v[4], v[5], v[6], v[7]};
}

i16x8 power_shufflehi_i16x8(i16x8 v, unsigned imm)
{
    return (i16x8){v[0], v[1], v[2], v[3],
                    v[4 + ((imm >> 0) & 3U)], v[4 + ((imm >> 2) & 3U)],
                    v[4 + ((imm >> 4) & 3U)], v[4 + ((imm >> 6) & 3U)]};
}

i16x8 power_sll_i16x8(i16x8 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 15U) {
        return (i16x8)vec_splats((unsigned short)0);
    }
    return (i16x8)vec_sl((u16x8)a, vec_splats((unsigned short)n));
}

i16x8 power_srl_i16x8(i16x8 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 15U) {
        return (i16x8)vec_splats((unsigned short)0);
    }
    return (i16x8)vec_sr((u16x8)a, vec_splats((unsigned short)n));
}

i16x8 power_sra_i16x8(i16x8 a, u64x2 count)
{
    unsigned long long raw = count[0];
    unsigned short n = (unsigned short)(raw > 15U ? 15U : raw);
    return vec_sra(a, vec_splats(n));
}

u16x8 power_cmplt_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_cmpgt((i16x8)b, (i16x8)a);
}

i16x8 power_set_i16x8(short lane7, short lane6, short lane5, short lane4,
                       short lane3, short lane2, short lane1, short lane0)
{
    return (i16x8){lane0, lane1, lane2, lane3,
                    lane4, lane5, lane6, lane7};
}

unsigned power_extract_i16x8(i16x8 a, unsigned imm)
{
    return (unsigned)(unsigned short)a[imm & 7U];
}

i16x8 power_insert_i16x8(i16x8 a, int value, unsigned imm)
{
    a[imm & 7U] = (short)value;
    return a;
}
