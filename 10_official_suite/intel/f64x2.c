#include <emmintrin.h>

typedef __m128d f64x2;
typedef __m128i i32x4;

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

f64x2 intel_shuffle_f64x2(f64x2 a, f64x2 b, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_shuffle_pd(a, b, 0);
    case 1: return _mm_shuffle_pd(a, b, 1);
    case 2: return _mm_shuffle_pd(a, b, 2);
    case 3: return _mm_shuffle_pd(a, b, 3);
    default: return a;
    }
}

f64x2 intel_set_f64x2(double high, double low)
{
    return _mm_set_pd(high, low);
}

f64x2 intel_cast_i64x2_f64x2(__m128i value)
{
    return _mm_castsi128_pd(value);
}

__m128i intel_cast_f64x2_i64x2(f64x2 value)
{
    return _mm_castpd_si128(value);
}

f64x2 intel_andnot_f64x2(f64x2 a, f64x2 b)
{
    return _mm_andnot_pd(a, b);
}

int intel_movemask_f64x2(f64x2 value)
{
    return _mm_movemask_pd(value);
}

f64x2 intel_cmpnlt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpnlt_pd(a, b);
}

f64x2 intel_cmpnle_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpnle_pd(a, b);
}

f64x2 intel_cmpngt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpngt_pd(a, b);
}

f64x2 intel_cmpnge_f64x2(f64x2 a, f64x2 b)
{
    return _mm_cmpnge_pd(a, b);
}

f64x2 intel_min_f64x2(f64x2 a, f64x2 b)
{
    return _mm_min_pd(a, b);
}

f64x2 intel_max_f64x2(f64x2 a, f64x2 b)
{
    return _mm_max_pd(a, b);
}

int intel_comieq_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comieq_sd(a, b);
}

int intel_comilt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comilt_sd(a, b);
}

int intel_comile_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comile_sd(a, b);
}

int intel_comigt_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comigt_sd(a, b);
}

int intel_comige_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comige_sd(a, b);
}

int intel_comineq_f64x2(f64x2 a, f64x2 b)
{
    return _mm_comineq_sd(a, b);
}

i32x4 intel_cvt_f64x2_i32x4(f64x2 a)
{
    return _mm_cvtpd_epi32(a);
}

i32x4 intel_cvtt_f64x2_i32x4(f64x2 a)
{
    return _mm_cvttpd_epi32(a);
}

f64x2 intel_add_scalar_f64x2(f64x2 a, f64x2 b)
{
    return _mm_add_sd(a, b);
}

f64x2 intel_loadu_f64x2(const void *source)
{
    return _mm_loadu_pd((const double *)source);
}
