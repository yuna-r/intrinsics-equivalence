#include <altivec.h>

typedef __vector signed int example_i32x4;
typedef __vector unsigned int example_u32x4;

example_u32x4 openpower_example_add_i32x4(example_u32x4 a,
                                         example_u32x4 b)
{
    return a + b;
}

example_u32x4 openpower_example_sub_i32x4(example_u32x4 a,
                                         example_u32x4 b)
{
    return a - b;
}

example_u32x4 openpower_example_and_i32x4(example_u32x4 a,
                                         example_u32x4 b)
{
    return a & b;
}

example_u32x4 openpower_example_or_i32x4(example_u32x4 a,
                                        example_u32x4 b)
{
    return a | b;
}

example_u32x4 openpower_example_xor_i32x4(example_u32x4 a,
                                         example_u32x4 b)
{
    return a ^ b;
}

example_u32x4 openpower_example_andnot_i32x4(example_u32x4 a,
                                            example_u32x4 b)
{
    return (~a) & b;
}

example_u32x4 openpower_example_cmpeq_i32x4(example_u32x4 a,
                                           example_u32x4 b)
{
    return (example_u32x4)vec_cmpeq(a, b);
}

example_u32x4 openpower_example_cmpgt_i32x4(example_u32x4 a,
                                           example_u32x4 b)
{
    return (example_u32x4)vec_cmpgt((example_i32x4)a,
                                    (example_i32x4)b);
}

example_u32x4 openpower_example_slli_i32x4(example_u32x4 value,
                                           unsigned int immediate)
{
    if (immediate > 31U) {
        return vec_splats(0U);
    }
    return vec_sl(value, vec_splats(immediate));
}

example_u32x4 openpower_example_srli_i32x4(example_u32x4 value,
                                           unsigned int immediate)
{
    if (immediate > 31U) {
        return vec_splats(0U);
    }
    return vec_sr(value, vec_splats(immediate));
}

example_u32x4 openpower_example_srai_i32x4(example_u32x4 value,
                                           unsigned int immediate)
{
    unsigned int count = immediate > 31U ? 31U : immediate;
    return (example_u32x4)vec_sra((example_i32x4)value,
                                  vec_splats(count));
}

example_u32x4 openpower_example_shuffle_i32x4(example_u32x4 value,
                                              unsigned int immediate)
{
    return (example_u32x4){
        value[(immediate >> 0) & 3U],
        value[(immediate >> 2) & 3U],
        value[(immediate >> 4) & 3U],
        value[(immediate >> 6) & 3U]
    };
}

example_u32x4 openpower_example_unpacklo_i32x4(example_u32x4 a,
                                               example_u32x4 b)
{
    return (example_u32x4){a[0], b[0], a[1], b[1]};
}

example_u32x4 openpower_example_unpackhi_i32x4(example_u32x4 a,
                                               example_u32x4 b)
{
    return (example_u32x4){a[2], b[2], a[3], b[3]};
}
