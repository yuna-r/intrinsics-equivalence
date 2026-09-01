#include <altivec.h>

typedef __vector double f64x2;
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
