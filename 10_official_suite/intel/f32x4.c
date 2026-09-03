#include "../shortcuts.h"
#include <emmintrin.h>

typedef __m128 f32x4;
typedef __m128d f64x2;
typedef __m128i i32x4;

f32x4 intel_set_f32x4(float lane3, float lane2, float lane1, float lane0)
{
    return _mm_set_ps(lane3, lane2, lane1, lane0);
}

f32x4 intel_setr_f32x4(float lane0, float lane1, float lane2, float lane3)
{
    return _mm_setr_ps(lane0, lane1, lane2, lane3);
}

f32x4 intel_set1_f32x4(float value)
{
    return _mm_set1_ps(value);
}

f32x4 intel_set_scalar_f32x4(float value)
{
    return _mm_set_ss(value);
}

f32x4 intel_load1_f32x4(const void *source)
{
    return _mm_load1_ps((const float *)source);
}

IOITF_UNARY(f32x4, f64x2, intel_cast_f64x2_f32x4, _mm_castpd_ps(a))
IOITF_UNARY(f64x2, f32x4, intel_cast_f32x4_f64x2, _mm_castps_pd(a))
IOITF_UNARY(i32x4, f32x4, intel_cast_f32x4_i32x4, _mm_castps_si128(a))
IOITF_UNARY(f32x4, i32x4, intel_cast_i32x4_f32x4, _mm_castsi128_ps(a))
IOITF_UNARY(int, f32x4, intel_movemask_f32x4, _mm_movemask_ps(a))
IOITF_BINARY(f32x4, f32x4, intel_unpacklo_f32x4, _mm_unpacklo_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_unpackhi_f32x4, _mm_unpackhi_ps(a, b))
IOITF_UNARY(f64x2, f32x4, intel_cvt_f32x4_f64x2, _mm_cvtps_pd(a))
IOITF_UNARY(f64x2, i32x4, intel_cvt_i32x4_f64x2, _mm_cvtepi32_pd(a))

f32x4 intel_cvt_scalar_f64x2_f32x4(f32x4 a, f64x2 b)
{
    return _mm_cvtsd_ss(a, b);
}

f64x2 intel_cvt_scalar_f32x4_f64x2(f64x2 a, f32x4 b)
{
    return _mm_cvtss_sd(a, b);
}

f32x4 intel_cvt_i32_f32x4(f32x4 a, int value)
{
    return _mm_cvtsi32_ss(a, value);
}

f64x2 intel_cvt_i32_f64x2(f64x2 a, int value)
{
    return _mm_cvtsi32_sd(a, value);
}

f64x2 intel_cvt_i64_f64x2(f64x2 a, long long value)
{
    return _mm_cvtsi64_sd(a, value);
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

IOITF_BINARY(f32x4, f32x4, intel_movehl_f32x4, _mm_movehl_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_movelh_f32x4, _mm_movelh_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_move_f32x4, _mm_move_ss(a, b))
IOITF_UNARY(f32x4, f64x2, intel_cvt_f64x2_f32x4, _mm_cvtpd_ps(a))
IOITF_UNARY(f32x4, i32x4, intel_cvt_i32x4_f32x4, _mm_cvtepi32_ps(a))
IOITF_UNARY(i32x4, f32x4, intel_cvt_f32x4_i32x4, _mm_cvtps_epi32(a))
IOITF_UNARY(i32x4, f32x4, intel_cvtt_f32x4_i32x4, _mm_cvttps_epi32(a))
IOITF_UNARY(int, f32x4, intel_cvt_scalar_f32x4_i32, _mm_cvtss_si32(a))
IOITF_UNARY(int, f32x4, intel_cvtt_scalar_f32x4_i32, _mm_cvttss_si32(a))
IOITF_BINARY(f32x4, f32x4, intel_add_f32x4, _mm_add_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_sub_f32x4, _mm_sub_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_mul_f32x4, _mm_mul_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_div_f32x4, _mm_div_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_add_scalar_f32x4, _mm_add_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_sub_scalar_f32x4, _mm_sub_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_mul_scalar_f32x4, _mm_mul_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_div_scalar_f32x4, _mm_div_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_and_f32x4, _mm_and_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_or_f32x4, _mm_or_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_xor_f32x4, _mm_xor_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_andnot_f32x4, _mm_andnot_ps(a, b))
IOITF_UNARY(f32x4, f32x4, intel_sqrt_f32x4, _mm_sqrt_ps(a))
IOITF_UNARY(f32x4, f32x4, intel_sqrt_scalar_f32x4, _mm_sqrt_ss(a))
IOITF_BINARY(f32x4, f32x4, intel_min_f32x4, _mm_min_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_max_f32x4, _mm_max_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_min_scalar_f32x4, _mm_min_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_max_scalar_f32x4, _mm_max_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpeq_f32x4, _mm_cmpeq_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpeq_scalar_f32x4, _mm_cmpeq_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpneq_f32x4, _mm_cmpneq_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpneq_scalar_f32x4, _mm_cmpneq_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmplt_f32x4, _mm_cmplt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmplt_scalar_f32x4, _mm_cmplt_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmple_f32x4, _mm_cmple_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmple_scalar_f32x4, _mm_cmple_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpgt_f32x4, _mm_cmpgt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpgt_scalar_f32x4, _mm_cmpgt_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpge_f32x4, _mm_cmpge_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpge_scalar_f32x4, _mm_cmpge_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnlt_f32x4, _mm_cmpnlt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnlt_scalar_f32x4, _mm_cmpnlt_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnle_f32x4, _mm_cmpnle_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnle_scalar_f32x4, _mm_cmpnle_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpngt_f32x4, _mm_cmpngt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpngt_scalar_f32x4, _mm_cmpngt_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnge_f32x4, _mm_cmpnge_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnge_scalar_f32x4, _mm_cmpnge_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpord_f32x4, _mm_cmpord_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpord_scalar_f32x4, _mm_cmpord_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpunord_f32x4, _mm_cmpunord_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpunord_scalar_f32x4, _mm_cmpunord_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comieq_f32x4, _mm_comieq_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comilt_f32x4, _mm_comilt_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comile_f32x4, _mm_comile_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comigt_f32x4, _mm_comigt_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comige_f32x4, _mm_comige_ss(a, b))
IOITF_BINARY(int, f32x4, intel_comineq_f32x4, _mm_comineq_ss(a, b))

f32x4 intel_load_scalar_f32x4(const void *source)
{
    return _mm_load_ss((const float *)source);
}

f32x4 intel_loadu_f32x4(const void *source)
{
    return _mm_loadu_ps((const float *)source);
}

f32x4 intel_loadr_f32x4(const void *source)
{
    return _mm_loadr_ps((const float *)source);
}

void intel_store_scalar_f32x4(void *destination, f32x4 a)
{
    _mm_store_ss((float *)destination, a);
}

void intel_storeu_f32x4(void *destination, f32x4 a)
{
    _mm_storeu_ps((float *)destination, a);
}

void intel_storer_f32x4(void *destination, f32x4 a)
{
    _mm_storer_ps((float *)destination, a);
}
