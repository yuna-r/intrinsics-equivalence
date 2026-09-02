#include "../shortcuts.h"
#include <altivec.h>

typedef __vector signed int i32x4;
typedef __vector unsigned int u32x4;
typedef __vector signed short i16x8;
typedef __vector unsigned long long u64x2;

IOITF_BINARY(u32x4, u32x4, power_add_i32x4, a + b)
IOITF_BINARY(u32x4, u32x4, power_sub_i32x4, a - b)
IOITF_BINARY(u32x4, u32x4, power_and_i32x4, a & b)
IOITF_BINARY(u32x4, u32x4, power_or_i32x4, a | b)
IOITF_BINARY(u32x4, u32x4, power_xor_i32x4, a ^ b)
IOITF_BINARY(u32x4, u32x4, power_andnot_i32x4, (~a) & b)
IOITF_BINARY(u32x4, u32x4, power_cmpeq_i32x4, (u32x4)vec_cmpeq(a, b))
IOITF_BINARY(u32x4, u32x4, power_cmpgt_i32x4, (u32x4)vec_cmpgt((i32x4)a, (i32x4)b))

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

IOITF_BINARY(u32x4, u32x4, power_unpacklo_i32x4, (u32x4){a[0], b[0], a[1], b[1]})
IOITF_BINARY(u32x4, u32x4, power_unpackhi_i32x4, (u32x4){a[2], b[2], a[3], b[3]})

u64x2 power_mul_u32x4(u32x4 a, u32x4 b)
{
    return (u64x2){(unsigned long long)a[0] * b[0],
                    (unsigned long long)a[2] * b[2]};
}

IOITF_BINARY(i16x8, i32x4, power_packs_i32x4, vec_packs(a, b))

i32x4 power_cvtsi32_i32x4(int value)
{
    return (i32x4){value, 0, 0, 0};
}

i32x4 power_set1_i32x4(int value)
{
    return vec_splats(value);
}

u32x4 power_sll_i32x4(u32x4 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 31U) {
        return vec_splats(0U);
    }
    return vec_sl(a, vec_splats((unsigned)n));
}

u32x4 power_srl_i32x4(u32x4 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 31U) {
        return vec_splats(0U);
    }
    return vec_sr(a, vec_splats((unsigned)n));
}

u32x4 power_sra_i32x4(u32x4 a, u64x2 count)
{
    unsigned long long raw = count[0];
    unsigned n = (unsigned)(raw > 31U ? 31U : raw);
    return (u32x4)vec_sra((i32x4)a, vec_splats(n));
}

IOITF_BINARY(u32x4, u32x4, power_cmplt_i32x4, (u32x4)vec_cmpgt((i32x4)b, (i32x4)a))
IOITF_UNARY(int, i32x4, power_cvtsi128_i32x4, a[0])

i32x4 power_set_i32x4(int lane3, int lane2, int lane1, int lane0)
{
    return (i32x4){lane0, lane1, lane2, lane3};
}

i32x4 power_setr_i32x4(int lane0, int lane1, int lane2, int lane3)
{
    return (i32x4){lane0, lane1, lane2, lane3};
}
