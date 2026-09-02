#include "../shortcuts.h"
#include <altivec.h>

typedef __vector signed char i8x16;
typedef __vector unsigned char u8x16;
typedef __vector unsigned long long u64x2;

IOITF_BINARY(u8x16, u8x16, power_add_i8x16, a + b)
IOITF_BINARY(u8x16, u8x16, power_sub_i8x16, a - b)
IOITF_BINARY(u8x16, u8x16, power_adds_i8x16, (u8x16)vec_adds((i8x16)a, (i8x16)b))
IOITF_BINARY(u8x16, u8x16, power_adds_u8x16, vec_adds(a, b))
IOITF_BINARY(u8x16, u8x16, power_subs_i8x16, (u8x16)vec_subs((i8x16)a, (i8x16)b))
IOITF_BINARY(u8x16, u8x16, power_subs_u8x16, vec_subs(a, b))
IOITF_BINARY(u8x16, u8x16, power_cmpeq_i8x16, (u8x16)vec_cmpeq(a, b))
IOITF_BINARY(u8x16, u8x16, power_cmpgt_i8x16, (u8x16)vec_cmpgt((i8x16)a, (i8x16)b))
IOITF_BINARY(u8x16, u8x16, power_avg_u8x16, vec_avg(a, b))

u64x2 power_sad_u8x16(u8x16 a, u8x16 b)
{
    unsigned long long low = 0;
    unsigned long long high = 0;
    unsigned lane;

    for (lane = 0; lane < 8; ++lane) {
        low += a[lane] > b[lane] ? a[lane] - b[lane] : b[lane] - a[lane];
    }
    for (lane = 8; lane < 16; ++lane) {
        high += a[lane] > b[lane] ? a[lane] - b[lane] : b[lane] - a[lane];
    }
    return (u64x2){low, high};
}

IOITF_BINARY(u8x16, u8x16, power_min_u8x16, vec_min(a, b))
IOITF_BINARY(u8x16, u8x16, power_max_u8x16, vec_max(a, b))

u8x16 power_slli_bytes_u8x16(u8x16 v, unsigned imm)
{
    const u8x16 zero = vec_splats((unsigned char)0);

    switch (imm) {
    case 0:
        return v;
    case 1:
        return (u8x16){0, v[0], v[1], v[2], v[3], v[4], v[5], v[6],
                       v[7], v[8], v[9], v[10], v[11], v[12], v[13], v[14]};
    case 7:
        return (u8x16){0, 0, 0, 0, 0, 0, 0, v[0],
                       v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8]};
    case 15:
        return (u8x16){0, 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, 0, v[0]};
    case 16:
    case 255:
        return zero;
    default:
        return v;
    }
}

u8x16 power_srli_bytes_u8x16(u8x16 v, unsigned imm)
{
    const u8x16 zero = vec_splats((unsigned char)0);

    switch (imm) {
    case 0:
        return v;
    case 1:
        return (u8x16){v[1], v[2], v[3], v[4], v[5], v[6], v[7], v[8],
                       v[9], v[10], v[11], v[12], v[13], v[14], v[15], 0};
    case 7:
        return (u8x16){v[7], v[8], v[9], v[10], v[11], v[12], v[13], v[14],
                       v[15], 0, 0, 0, 0, 0, 0, 0};
    case 15:
        return (u8x16){v[15], 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, 0, 0};
    case 16:
    case 255:
        return zero;
    default:
        return v;
    }
}

u8x16 power_unpacklo_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16){a[0], b[0], a[1], b[1], a[2], b[2], a[3], b[3],
                    a[4], b[4], a[5], b[5], a[6], b[6], a[7], b[7]};
}

u8x16 power_unpackhi_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16){a[8], b[8], a[9], b[9], a[10], b[10], a[11], b[11],
                    a[12], b[12], a[13], b[13], a[14], b[14], a[15], b[15]};
}

int power_movemask_i8x16(u8x16 v)
{
    unsigned result = 0;
    unsigned lane;

    for (lane = 0; lane < 16; ++lane) {
        result |= ((unsigned)(v[lane] >> 7) & 1U) << lane;
    }
    return (int)result;
}

IOITF_BINARY(u8x16, u8x16, power_cmplt_i8x16, (u8x16)vec_cmpgt((i8x16)b, (i8x16)a))

i8x16 power_set_i8x16(signed char lane15, signed char lane14,
                       signed char lane13, signed char lane12,
                       signed char lane11, signed char lane10,
                       signed char lane9, signed char lane8,
                       signed char lane7, signed char lane6,
                       signed char lane5, signed char lane4,
                       signed char lane3, signed char lane2,
                       signed char lane1, signed char lane0)
{
    return (i8x16){lane0, lane1, lane2, lane3,
                    lane4, lane5, lane6, lane7,
                    lane8, lane9, lane10, lane11,
                    lane12, lane13, lane14, lane15};
}
