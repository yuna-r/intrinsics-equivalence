#include <emmintrin.h>

typedef __m128 f32x4;
typedef __m128d f64x2;
typedef __m128i i32x4;

f32x4 intel_cast_f64x2_f32x4(f64x2 a)
{
    return _mm_castpd_ps(a);
}

f64x2 intel_cast_f32x4_f64x2(f32x4 a)
{
    return _mm_castps_pd(a);
}

i32x4 intel_cast_f32x4_i32x4(f32x4 a)
{
    return _mm_castps_si128(a);
}

f32x4 intel_cast_i32x4_f32x4(i32x4 a)
{
    return _mm_castsi128_ps(a);
}
