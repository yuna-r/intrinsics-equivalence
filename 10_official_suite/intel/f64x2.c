#include <emmintrin.h>

typedef __m128d example_f64x2;

example_f64x2 intel_example_add_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_add_pd(a, b);
}

example_f64x2 intel_example_sub_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_sub_pd(a, b);
}

example_f64x2 intel_example_mul_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_mul_pd(a, b);
}

example_f64x2 intel_example_and_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_and_pd(a, b);
}

example_f64x2 intel_example_or_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_or_pd(a, b);
}

example_f64x2 intel_example_xor_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_xor_pd(a, b);
}

example_f64x2 intel_example_set1_f64x2(double value)
{
    return _mm_set1_pd(value);
}

example_f64x2 intel_example_move_f64x2(example_f64x2 a, example_f64x2 b)
{
    return _mm_move_sd(a, b);
}

example_f64x2 intel_example_unpacklo_f64x2(example_f64x2 a,
                                           example_f64x2 b)
{
    return _mm_unpacklo_pd(a, b);
}

example_f64x2 intel_example_unpackhi_f64x2(example_f64x2 a,
                                           example_f64x2 b)
{
    return _mm_unpackhi_pd(a, b);
}
