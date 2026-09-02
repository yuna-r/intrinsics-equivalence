#include "../shortcuts.h"
#include <altivec.h>

typedef __vector signed long long i64x2;
typedef __vector unsigned long long u64x2;

IOITF_BINARY(i64x2, i64x2, power_add_i64x2, (i64x2)((u64x2)a + (u64x2)b))
IOITF_BINARY(i64x2, i64x2, power_sub_i64x2, (i64x2)((u64x2)a - (u64x2)b))

i64x2 power_slli_i64x2(i64x2 v, unsigned imm)
{
    if (imm > 63U) {
        return (i64x2)vec_splats(0ULL);
    }
    return (i64x2)vec_sl((u64x2)v, vec_splats((unsigned long long)imm));
}

i64x2 power_srli_i64x2(i64x2 v, unsigned imm)
{
    if (imm > 63U) {
        return (i64x2)vec_splats(0ULL);
    }
    return (i64x2)vec_sr((u64x2)v, vec_splats((unsigned long long)imm));
}

IOITF_BINARY(i64x2, i64x2, power_unpacklo_i64x2, (i64x2){a[0], b[0]})
IOITF_BINARY(i64x2, i64x2, power_unpackhi_i64x2, (i64x2){a[1], b[1]})

i64x2 power_move_i64x2(i64x2 value)
{
    return (i64x2){value[0], 0};
}

i64x2 power_cvtsi64_i64x2(long long value)
{
    return (i64x2){value, 0};
}

i64x2 power_set1_i64x2(long long value)
{
    return vec_splats(value);
}

i64x2 power_sll_i64x2(i64x2 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 63U) {
        return (i64x2)vec_splats(0ULL);
    }
    return (i64x2)vec_sl((u64x2)a, vec_splats(n));
}

i64x2 power_srl_i64x2(i64x2 a, u64x2 count)
{
    unsigned long long n = count[0];
    if (n > 63U) {
        return (i64x2)vec_splats(0ULL);
    }
    return (i64x2)vec_sr((u64x2)a, vec_splats(n));
}

IOITF_UNARY(long long, i64x2, power_cvtsi128_i64x2, a[0])

i64x2 power_set_i64x2(long long high, long long low)
{
    return (i64x2){low, high};
}
