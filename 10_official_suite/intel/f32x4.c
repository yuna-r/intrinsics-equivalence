#include "../shortcuts.h"
#include <emmintrin.h>

typedef __m128 f32x4;
typedef __m128d f64x2;
typedef __m128i i32x4;

IOITF_UNARY(f32x4, f64x2, intel_cast_f64x2_f32x4, _mm_castpd_ps(a))
IOITF_UNARY(f64x2, f32x4, intel_cast_f32x4_f64x2, _mm_castps_pd(a))
IOITF_UNARY(i32x4, f32x4, intel_cast_f32x4_i32x4, _mm_castps_si128(a))
IOITF_UNARY(f32x4, i32x4, intel_cast_i32x4_f32x4, _mm_castsi128_ps(a))
IOITF_UNARY(int, f32x4, intel_movemask_f32x4, _mm_movemask_ps(a))
IOITF_BINARY(f32x4, f32x4, intel_unpacklo_f32x4, _mm_unpacklo_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_unpackhi_f32x4, _mm_unpackhi_ps(a, b))
IOITF_UNARY(f64x2, f32x4, intel_cvt_f32x4_f64x2, _mm_cvtps_pd(a))
IOITF_UNARY(f64x2, i32x4, intel_cvt_i32x4_f64x2, _mm_cvtepi32_pd(a))

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
IOITF_BINARY(f32x4, f32x4, intel_add_f32x4, _mm_add_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_sub_f32x4, _mm_sub_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_mul_f32x4, _mm_mul_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_add_scalar_f32x4, _mm_add_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_sub_scalar_f32x4, _mm_sub_ss(a, b))
IOITF_BINARY(f32x4, f32x4, intel_mul_scalar_f32x4, _mm_mul_ss(a, b))
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
IOITF_BINARY(f32x4, f32x4, intel_cmpneq_f32x4, _mm_cmpneq_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmplt_f32x4, _mm_cmplt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmple_f32x4, _mm_cmple_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpgt_f32x4, _mm_cmpgt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpge_f32x4, _mm_cmpge_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnlt_f32x4, _mm_cmpnlt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnle_f32x4, _mm_cmpnle_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpngt_f32x4, _mm_cmpngt_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpnge_f32x4, _mm_cmpnge_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpord_f32x4, _mm_cmpord_ps(a, b))
IOITF_BINARY(f32x4, f32x4, intel_cmpunord_f32x4, _mm_cmpunord_ps(a, b))
