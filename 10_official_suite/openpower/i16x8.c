#include <altivec.h>

typedef __vector signed short i16x8;
typedef __vector unsigned short u16x8;

u16x8 power_add_i16x8(u16x8 a, u16x8 b)
{
    return a + b;
}

u16x8 power_sub_i16x8(u16x8 a, u16x8 b)
{
    return a - b;
}

u16x8 power_adds_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_adds((i16x8)a, (i16x8)b);
}

u16x8 power_adds_u16x8(u16x8 a, u16x8 b)
{
    return vec_adds(a, b);
}

u16x8 power_subs_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_subs((i16x8)a, (i16x8)b);
}

u16x8 power_subs_u16x8(u16x8 a, u16x8 b)
{
    return vec_subs(a, b);
}

u16x8 power_cmpeq_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_cmpeq(a, b);
}

u16x8 power_cmpgt_i16x8(u16x8 a, u16x8 b)
{
    return (u16x8)vec_cmpgt((i16x8)a, (i16x8)b);
}
