#include <altivec.h>

typedef __vector double f64x2;
typedef __vector signed long long i64x2;
typedef __vector unsigned long long u64x2;

f64x2 power_add_f64x2(f64x2 a, f64x2 b)
{
    return vec_add(a, b);
}

f64x2 power_sub_f64x2(f64x2 a, f64x2 b)
{
    return vec_sub(a, b);
}

f64x2 power_mul_f64x2(f64x2 a, f64x2 b)
{
    return vec_mul(a, b);
}

f64x2 power_and_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)((u64x2)a & (u64x2)b);
}

f64x2 power_or_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)((u64x2)a | (u64x2)b);
}

f64x2 power_xor_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)((u64x2)a ^ (u64x2)b);
}

f64x2 power_set1_f64x2(double x)
{
    return vec_splats(x);
}

f64x2 power_move_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2){b[0], a[1]};
}

f64x2 power_unpacklo_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2){a[0], b[0]};
}

f64x2 power_unpackhi_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2){a[1], b[1]};
}

static unsigned long long mask(int yes)
{
    return yes ? ~0ULL : 0ULL;
}

static int ordered(double a, double b)
{
    return a == a && b == b;
}

f64x2 power_cmpeq_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] == b[0]), mask(a[1] == b[1])};
}

f64x2 power_cmplt_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] < b[0]), mask(a[1] < b[1])};
}

f64x2 power_cmple_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] <= b[0]), mask(a[1] <= b[1])};
}

f64x2 power_cmpgt_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] > b[0]), mask(a[1] > b[1])};
}

f64x2 power_cmpge_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] >= b[0]), mask(a[1] >= b[1])};
}

f64x2 power_cmpneq_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(a[0] != b[0]), mask(a[1] != b[1])};
}

f64x2 power_cmpord_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(ordered(a[0], b[0])), mask(ordered(a[1], b[1]))};
}

f64x2 power_cmpunord_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(!ordered(a[0], b[0])), mask(!ordered(a[1], b[1]))};
}

f64x2 power_shuffle_f64x2(f64x2 a, f64x2 b, unsigned imm)
{
    return (f64x2){a[imm & 1U], b[(imm >> 1) & 1U]};
}

f64x2 power_set_f64x2(double high, double low)
{
    return (f64x2){low, high};
}

f64x2 power_cast_i64x2_f64x2(i64x2 value)
{
    return (f64x2)value;
}

i64x2 power_cast_f64x2_i64x2(f64x2 value)
{
    return (i64x2)value;
}

f64x2 power_andnot_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)((~(u64x2)a) & (u64x2)b);
}

int power_movemask_f64x2(f64x2 value)
{
    u64x2 bits = (u64x2)value;
    return (int)((bits[0] >> 63) | ((bits[1] >> 63) << 1));
}

f64x2 power_cmpnlt_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(!(a[0] < b[0])), mask(!(a[1] < b[1]))};
}

f64x2 power_cmpnle_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(!(a[0] <= b[0])), mask(!(a[1] <= b[1]))};
}

f64x2 power_cmpngt_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(!(a[0] > b[0])), mask(!(a[1] > b[1]))};
}

f64x2 power_cmpnge_f64x2(f64x2 a, f64x2 b)
{
    return (f64x2)(u64x2){mask(!(a[0] >= b[0])), mask(!(a[1] >= b[1]))};
}

static int nan_bits(unsigned long long bits)
{
    return (bits & 0x7ff0000000000000ULL) == 0x7ff0000000000000ULL &&
           (bits & 0x000fffffffffffffULL) != 0;
}

static unsigned long long minmax_bits(double a, double b,
                                      unsigned long long a_bits,
                                      unsigned long long b_bits,
                                      int select_min)
{
    if (nan_bits(a_bits) || nan_bits(b_bits) || a == b) {
        return b_bits;
    }
    if ((select_min && a < b) || (!select_min && a > b)) {
        return a_bits;
    }
    return b_bits;
}

f64x2 power_min_f64x2(f64x2 a, f64x2 b)
{
    u64x2 a_bits = (u64x2)a;
    u64x2 b_bits = (u64x2)b;
    return (f64x2)(u64x2){
        minmax_bits(a[0], b[0], a_bits[0], b_bits[0], 1),
        minmax_bits(a[1], b[1], a_bits[1], b_bits[1], 1)};
}

f64x2 power_max_f64x2(f64x2 a, f64x2 b)
{
    u64x2 a_bits = (u64x2)a;
    u64x2 b_bits = (u64x2)b;
    return (f64x2)(u64x2){
        minmax_bits(a[0], b[0], a_bits[0], b_bits[0], 0),
        minmax_bits(a[1], b[1], a_bits[1], b_bits[1], 0)};
}

int power_comieq_f64x2(f64x2 a, f64x2 b)
{
    return ordered(a[0], b[0]) && a[0] == b[0];
}

int power_comilt_f64x2(f64x2 a, f64x2 b)
{
    return ordered(a[0], b[0]) && a[0] < b[0];
}

int power_comile_f64x2(f64x2 a, f64x2 b)
{
    return ordered(a[0], b[0]) && a[0] <= b[0];
}

int power_comigt_f64x2(f64x2 a, f64x2 b)
{
    return ordered(a[0], b[0]) && a[0] > b[0];
}

int power_comige_f64x2(f64x2 a, f64x2 b)
{
    return ordered(a[0], b[0]) && a[0] >= b[0];
}

int power_comineq_f64x2(f64x2 a, f64x2 b)
{
    return !ordered(a[0], b[0]) || a[0] != b[0];
}
