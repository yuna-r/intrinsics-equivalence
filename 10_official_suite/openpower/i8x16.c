#include <altivec.h>

typedef __vector signed char i8x16;
typedef __vector unsigned char u8x16;

u8x16 power_add_i8x16(u8x16 a, u8x16 b)
{
    return a + b;
}

u8x16 power_sub_i8x16(u8x16 a, u8x16 b)
{
    return a - b;
}

u8x16 power_adds_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16)vec_adds((i8x16)a, (i8x16)b);
}

u8x16 power_adds_u8x16(u8x16 a, u8x16 b)
{
    return vec_adds(a, b);
}

u8x16 power_subs_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16)vec_subs((i8x16)a, (i8x16)b);
}

u8x16 power_subs_u8x16(u8x16 a, u8x16 b)
{
    return vec_subs(a, b);
}

u8x16 power_cmpeq_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16)vec_cmpeq(a, b);
}

u8x16 power_cmpgt_i8x16(u8x16 a, u8x16 b)
{
    return (u8x16)vec_cmpgt((i8x16)a, (i8x16)b);
}
