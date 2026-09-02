#include "../shortcuts.h"
#include <altivec.h>

typedef __vector float f32x4;
typedef __vector double f64x2;
typedef __vector signed int i32x4;
typedef __vector unsigned int u32x4;
typedef __vector unsigned long long u64x2;

f32x4 power_cast_f64x2_f32x4(f64x2 a)
{
    u64x2 bits = (u64x2)a;
    return (f32x4)(u32x4){
        (unsigned)bits[0], (unsigned)(bits[0] >> 32),
        (unsigned)bits[1], (unsigned)(bits[1] >> 32)};
}

f64x2 power_cast_f32x4_f64x2(f32x4 a)
{
    u32x4 bits = (u32x4)a;
    return (f64x2)(u64x2){
        (unsigned long long)bits[0] | ((unsigned long long)bits[1] << 32),
        (unsigned long long)bits[2] | ((unsigned long long)bits[3] << 32)};
}

IOITF_UNARY(i32x4, f32x4, power_cast_f32x4_i32x4, (i32x4)a)
IOITF_UNARY(f32x4, i32x4, power_cast_i32x4_f32x4, (f32x4)a)

int power_movemask_f32x4(f32x4 a)
{
    u32x4 bits = (u32x4)a;
    return (int)((bits[0] >> 31) | ((bits[1] >> 31) << 1) |
                 ((bits[2] >> 31) << 2) | ((bits[3] >> 31) << 3));
}

IOITF_BINARY(f32x4, f32x4, power_unpacklo_f32x4, (f32x4){a[0], b[0], a[1], b[1]})

static unsigned long long widen_f32_bits(unsigned bits)
{
    unsigned long long sign = (unsigned long long)(bits >> 31) << 63;
    unsigned exponent = (bits >> 23) & 0xffU;
    unsigned fraction = bits & 0x7fffffU;
    unsigned leading;

    if (exponent == 0xffU) {
        if (fraction == 0U) {
            return sign | 0x7ff0000000000000ULL;
        }
        return sign | 0x7ff0000000000000ULL |
               ((unsigned long long)fraction << 29) | (1ULL << 51);
    }
    if (exponent != 0U) {
        return sign | ((unsigned long long)(exponent + 896U) << 52) |
               ((unsigned long long)fraction << 29);
    }
    if (fraction == 0U) {
        return sign;
    }
    leading = 0U;
    while ((fraction >> (leading + 1U)) != 0U) {
        ++leading;
    }
    return sign | ((unsigned long long)(leading + 874U) << 52) |
           ((unsigned long long)(fraction - (1U << leading)) <<
            (52U - leading));
}

f64x2 power_cvt_f32x4_f64x2(f32x4 a)
{
    u32x4 bits = (u32x4)a;
    return (f64x2)(u64x2){widen_f32_bits(bits[0]),
                           widen_f32_bits(bits[1])};
}

IOITF_UNARY(f64x2, i32x4, power_cvt_i32x4_f64x2, (f64x2){(double)a[0], (double)a[1]})

f32x4 power_shuffle_f32x4(f32x4 a, f32x4 b, unsigned imm)
{
    return (f32x4){a[imm & 3U], a[(imm >> 2) & 3U],
                    b[(imm >> 4) & 3U], b[(imm >> 6) & 3U]};
}

IOITF_BINARY(f32x4, f32x4, power_movehl_f32x4, (f32x4){b[2], b[3], a[2], a[3]})

static unsigned long long round_shift_even(unsigned long long value,
                                           unsigned shift)
{
    unsigned long long quotient;
    unsigned long long remainder;
    unsigned long long halfway;

    if (shift == 0U) {
        return value;
    }
    if (shift >= 64U) {
        return 0;
    }
    quotient = value >> shift;
    remainder = value - (quotient << shift);
    halfway = 1ULL << (shift - 1U);
    if (remainder > halfway ||
        (remainder == halfway && (quotient & 1ULL) != 0U)) {
        ++quotient;
    }
    return quotient;
}

static unsigned narrow_f64_bits(unsigned long long bits)
{
    unsigned sign = (unsigned)(bits >> 63) << 31;
    unsigned exponent = (unsigned)((bits >> 52) & 0x7ffU);
    unsigned long long fraction = bits & 0x000fffffffffffffULL;
    unsigned long long significand;
    unsigned long long rounded;
    int unbiased;

    if (exponent == 0x7ffU) {
        if (fraction == 0U) {
            return sign | 0x7f800000U;
        }
        return sign | 0x7f800000U | (unsigned)(fraction >> 29) |
               0x00400000U;
    }
    if (exponent == 0U) {
        return sign;
    }
    unbiased = (int)exponent - 1023;
    significand = (1ULL << 52) | fraction;
    if (unbiased > 127) {
        return sign | 0x7f800000U;
    }
    if (unbiased >= -126) {
        rounded = round_shift_even(significand, 29U);
        if (rounded == (1ULL << 24)) {
            rounded >>= 1;
            ++unbiased;
            if (unbiased > 127) {
                return sign | 0x7f800000U;
            }
        }
        return sign | ((unsigned)(unbiased + 127) << 23) |
               ((unsigned)rounded & 0x007fffffU);
    }
    rounded = round_shift_even(significand, (unsigned)(-unbiased - 97));
    if (rounded >= (1ULL << 23)) {
        return sign | 0x00800000U;
    }
    return sign | (unsigned)rounded;
}

static unsigned convert_i32_f32_bits(int value)
{
    unsigned sign = value < 0 ? 0x80000000U : 0U;
    unsigned magnitude = value < 0 ? 0U - (unsigned)value : (unsigned)value;
    unsigned probe = magnitude;
    unsigned leading = 0;
    unsigned long long rounded;

    if (magnitude == 0U) {
        return 0U;
    }
    while (probe > 1U) {
        probe >>= 1;
        ++leading;
    }
    if (leading <= 23U) {
        rounded = (unsigned long long)magnitude << (23U - leading);
    } else {
        rounded = round_shift_even(magnitude, leading - 23U);
        if (rounded == (1ULL << 24)) {
            rounded >>= 1;
            ++leading;
        }
    }
    return sign | ((leading + 127U) << 23) |
           ((unsigned)rounded & 0x007fffffU);
}

static int nearest_f32_i32(float value)
{
    double widened = (double)value;
    long long integral;
    double fraction;

    if (widened != widened || widened < -2147483648.5 ||
        widened >= 2147483647.5) {
        return (-2147483647 - 1);
    }
    integral = (long long)widened;
    fraction = widened - (double)integral;
    if (fraction > 0.5 ||
        (fraction == 0.5 && integral % 2LL != 0LL)) {
        ++integral;
    } else if (fraction < -0.5 ||
               (fraction == -0.5 && integral % 2LL != 0LL)) {
        --integral;
    }
    return (int)integral;
}

static int truncate_f32_i32(float value)
{
    double widened = (double)value;
    if (widened != widened || widened < -2147483648.0 ||
        widened >= 2147483648.0) {
        return (-2147483647 - 1);
    }
    return (int)widened;
}

f32x4 power_cvt_f64x2_f32x4(f64x2 a)
{
    u64x2 bits = (u64x2)a;
    return (f32x4)(u32x4){narrow_f64_bits(bits[0]),
                           narrow_f64_bits(bits[1]), 0, 0};
}

f32x4 power_cvt_i32x4_f32x4(i32x4 a)
{
    return (f32x4)(u32x4){convert_i32_f32_bits(a[0]),
                           convert_i32_f32_bits(a[1]),
                           convert_i32_f32_bits(a[2]),
                           convert_i32_f32_bits(a[3])};
}

i32x4 power_cvt_f32x4_i32x4(f32x4 a)
{
    return (i32x4){nearest_f32_i32(a[0]), nearest_f32_i32(a[1]),
                    nearest_f32_i32(a[2]), nearest_f32_i32(a[3])};
}

i32x4 power_cvtt_f32x4_i32x4(f32x4 a)
{
    return (i32x4){truncate_f32_i32(a[0]), truncate_f32_i32(a[1]),
                    truncate_f32_i32(a[2]), truncate_f32_i32(a[3])};
}

IOITF_BINARY(f32x4, f32x4, power_add_f32x4, vec_add(a, b))

static unsigned sqrt_f32_bits(unsigned input, unsigned result)
{
    unsigned magnitude = input & 0x7fffffffU;
    if ((input & 0x7f800000U) == 0x7f800000U &&
        (input & 0x007fffffU) != 0U) {
        return input | 0x00400000U;
    }
    if ((input & 0x80000000U) != 0U && magnitude != 0U) {
        return 0xffc00000U;
    }
    return result;
}

f32x4 power_sqrt_f32x4(f32x4 a)
{
    u32x4 input = (u32x4)a;
    u32x4 result = (u32x4)vec_sqrt(a);
    return (f32x4)(u32x4){
        sqrt_f32_bits(input[0], result[0]),
        sqrt_f32_bits(input[1], result[1]),
        sqrt_f32_bits(input[2], result[2]),
        sqrt_f32_bits(input[3], result[3])};
}

static int nan_f32_bits(unsigned bits)
{
    return (bits & 0x7f800000U) == 0x7f800000U &&
           (bits & 0x007fffffU) != 0U;
}

static unsigned min_f32_bits(float a, float b, unsigned a_bits,
                             unsigned b_bits)
{
    if (nan_f32_bits(a_bits) || nan_f32_bits(b_bits) || a == b) {
        return b_bits;
    }
    return a < b ? a_bits : b_bits;
}

f32x4 power_min_f32x4(f32x4 a, f32x4 b)
{
    u32x4 a_bits = (u32x4)a;
    u32x4 b_bits = (u32x4)b;
    return (f32x4)(u32x4){
        min_f32_bits(a[0], b[0], a_bits[0], b_bits[0]),
        min_f32_bits(a[1], b[1], a_bits[1], b_bits[1]),
        min_f32_bits(a[2], b[2], a_bits[2], b_bits[2]),
        min_f32_bits(a[3], b[3], a_bits[3], b_bits[3])};
}

static unsigned mask_f32(int yes)
{
    return yes ? ~0U : 0U;
}

f32x4 power_cmpunord_f32x4(f32x4 a, f32x4 b)
{
    u32x4 a_bits = (u32x4)a;
    u32x4 b_bits = (u32x4)b;
    return (f32x4)(u32x4){
        mask_f32(nan_f32_bits(a_bits[0]) || nan_f32_bits(b_bits[0])),
        mask_f32(nan_f32_bits(a_bits[1]) || nan_f32_bits(b_bits[1])),
        mask_f32(nan_f32_bits(a_bits[2]) || nan_f32_bits(b_bits[2])),
        mask_f32(nan_f32_bits(a_bits[3]) || nan_f32_bits(b_bits[3]))};
}
