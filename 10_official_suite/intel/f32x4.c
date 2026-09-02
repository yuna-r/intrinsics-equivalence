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

int intel_movemask_f32x4(f32x4 a)
{
    return _mm_movemask_ps(a);
}

f32x4 intel_unpacklo_f32x4(f32x4 a, f32x4 b)
{
    return _mm_unpacklo_ps(a, b);
}

f64x2 intel_cvt_f32x4_f64x2(f32x4 a)
{
    return _mm_cvtps_pd(a);
}

f64x2 intel_cvt_i32x4_f64x2(i32x4 a)
{
    return _mm_cvtepi32_pd(a);
}

f32x4 intel_shuffle_f32x4(f32x4 a, f32x4 b, unsigned imm)
{
    switch (imm) {
    case 0: return _mm_shuffle_ps(a, b, 0);
    case 27: return _mm_shuffle_ps(a, b, 27);
    case 78: return _mm_shuffle_ps(a, b, 78);
    case 177: return _mm_shuffle_ps(a, b, 177);
    case 228: return _mm_shuffle_ps(a, b, 228);
    case 255: return _mm_shuffle_ps(a, b, 255);
    default: return a;
    }
}

f32x4 intel_movehl_f32x4(f32x4 a, f32x4 b)
{
    return _mm_movehl_ps(a, b);
}

f32x4 intel_cvt_f64x2_f32x4(f64x2 a)
{
    return _mm_cvtpd_ps(a);
}

f32x4 intel_cvt_i32x4_f32x4(i32x4 a)
{
    return _mm_cvtepi32_ps(a);
}

i32x4 intel_cvt_f32x4_i32x4(f32x4 a)
{
    return _mm_cvtps_epi32(a);
}

i32x4 intel_cvtt_f32x4_i32x4(f32x4 a)
{
    return _mm_cvttps_epi32(a);
}

f32x4 intel_add_f32x4(f32x4 a, f32x4 b)
{
    return _mm_add_ps(a, b);
}

f32x4 intel_sqrt_f32x4(f32x4 a)
{
    return _mm_sqrt_ps(a);
}

f32x4 intel_min_f32x4(f32x4 a, f32x4 b)
{
    return _mm_min_ps(a, b);
}

f32x4 intel_cmpunord_f32x4(f32x4 a, f32x4 b)
{
    return _mm_cmpunord_ps(a, b);
}
