#include <altivec.h>

typedef __vector double example_f64x2;
typedef __vector unsigned long long example_u64x2;

example_f64x2 openpower_example_add_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return vec_add(a, b);
}

example_f64x2 openpower_example_sub_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return vec_sub(a, b);
}

example_f64x2 openpower_example_mul_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return vec_mul(a, b);
}

example_f64x2 openpower_example_and_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return (example_f64x2)((example_u64x2)a & (example_u64x2)b);
}

example_f64x2 openpower_example_or_f64x2(example_f64x2 a,
                                         example_f64x2 b)
{
    return (example_f64x2)((example_u64x2)a | (example_u64x2)b);
}

example_f64x2 openpower_example_xor_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return (example_f64x2)((example_u64x2)a ^ (example_u64x2)b);
}

example_f64x2 openpower_example_set1_f64x2(double value)
{
    return vec_splats(value);
}

example_f64x2 openpower_example_move_f64x2(example_f64x2 a,
                                           example_f64x2 b)
{
    return (example_f64x2){b[0], a[1]};
}

example_f64x2 openpower_example_unpacklo_f64x2(example_f64x2 a,
                                               example_f64x2 b)
{
    return (example_f64x2){a[0], b[0]};
}

example_f64x2 openpower_example_unpackhi_f64x2(example_f64x2 a,
                                               example_f64x2 b)
{
    return (example_f64x2){a[1], b[1]};
}
