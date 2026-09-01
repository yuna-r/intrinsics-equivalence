#include <emmintrin.h>

typedef __m128d f64x2;

f64x2 intel_add_f64x2(f64x2 a, f64x2 b)
{
    return _mm_add_pd(a, b);
}

f64x2 intel_sub_f64x2(f64x2 a, f64x2 b)
{
    return _mm_sub_pd(a, b);
}

f64x2 intel_mul_f64x2(f64x2 a, f64x2 b)
{
    return _mm_mul_pd(a, b);
}

f64x2 intel_and_f64x2(f64x2 a, f64x2 b)
{
    return _mm_and_pd(a, b);
}

f64x2 intel_or_f64x2(f64x2 a, f64x2 b)
{
    return _mm_or_pd(a, b);
}

f64x2 intel_xor_f64x2(f64x2 a, f64x2 b)
{
    return _mm_xor_pd(a, b);
}

f64x2 intel_set1_f64x2(double x)
{
    return _mm_set1_pd(x);
}

f64x2 intel_move_f64x2(f64x2 a, f64x2 b)
{
    return _mm_move_sd(a, b);
}

f64x2 intel_unpacklo_f64x2(f64x2 a, f64x2 b)
{
    return _mm_unpacklo_pd(a, b);
}

f64x2 intel_unpackhi_f64x2(f64x2 a, f64x2 b)
{
    return _mm_unpackhi_pd(a, b);
}

f64x2 intel_cmpeq_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpeq_pd(a, b);
}

f64x2 intel_cmplt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmplt_pd(a, b);
}

f64x2 intel_cmple_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmple_pd(a, b);
}

f64x2 intel_cmpgt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpgt_pd(a, b);
}

f64x2 intel_cmpge_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpge_pd(a, b);
}

f64x2 intel_cmpneq_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpneq_pd(a, b);
}

f64x2 intel_cmpord_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpord_pd(a, b);
}

f64x2 intel_cmpunord_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpunord_pd(a, b);
}
