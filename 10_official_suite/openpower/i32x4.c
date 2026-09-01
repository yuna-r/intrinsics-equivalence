#include <altivec.h>

typedef __vector signed int i32x4;
typedef __vector unsigned int u32x4;
typedef __vector signed short i16x8;
typedef __vector unsigned long long u64x2;

u32x4 power_add_i32x4(u32x4 a, u32x4 b)
{
    return a + b;
}

u32x4 power_sub_i32x4(u32x4 a, u32x4 b)
{
    return a - b;
}

u32x4 power_and_i32x4(u32x4 a, u32x4 b)
{
    return a & b;
}

u32x4 power_or_i32x4(u32x4 a, u32x4 b)
{
    return a | b;
}

u32x4 power_xor_i32x4(u32x4 a, u32x4 b)
{
    return a ^ b;
}

u32x4 power_andnot_i32x4(u32x4 a, u32x4 b)
{
    return (~a) & b;
}

u32x4 power_cmpeq_i32x4(u32x4 a, u32x4 b)
{
    return (u32x4)vec_cmpeq(a, b);
}

u32x4 power_cmpgt_i32x4(u32x4 a, u32x4 b)
{
    return (u32x4)vec_cmpgt((i32x4)a, (i32x4)b);
}

u32x4 power_slli_i32x4(u32x4 v, unsigned imm)
{
    if (imm > 31U) {
        return vec_splats(0U);
    }
    return vec_sl(v, vec_splats(imm));
}

u32x4 power_srli_i32x4(u32x4 v, unsigned imm)
{
    if (imm > 31U) {
        return vec_splats(0U);
    }
    return vec_sr(v, vec_splats(imm));
}

u32x4 power_srai_i32x4(u32x4 v, unsigned imm)
{
    unsigned n = imm > 31U ? 31U : imm;
    return (u32x4)vec_sra((i32x4)v, vec_splats(n));
}

u32x4 power_shuffle_i32x4(u32x4 v, unsigned imm)
{
    return (u32x4){v[(imm >> 0) & 3U], v[(imm >> 2) & 3U],
                   v[(imm >> 4) & 3U], v[(imm >> 6) & 3U]};
}

u32x4 power_unpacklo_i32x4(u32x4 a, u32x4 b)
{
    return (u32x4){a[0], b[0], a[1], b[1]};
}

u32x4 power_unpackhi_i32x4(u32x4 a, u32x4 b)
{
    return (u32x4){a[2], b[2], a[3], b[3]};
}

u64x2 power_mul_u32x4(u32x4 a, u32x4 b)
{
    return (u64x2){(unsigned long long)a[0] * b[0],
                    (unsigned long long)a[2] * b[2]};
}

i16x8 power_packs_i32x4(i32x4 a, i32x4 b)
{
    return vec_packs(a, b);
}

i32x4 power_cvtsi32_i32x4(int value)
{
    return (i32x4){value, 0, 0, 0};
}

i32x4 power_set1_i32x4(int value)
{
    return vec_splats(value);
}
