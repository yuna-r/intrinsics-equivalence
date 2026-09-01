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

i32x4 power_cast_f32x4_i32x4(f32x4 a)
{
    return (i32x4)a;
}

f32x4 power_cast_i32x4_f32x4(i32x4 a)
{
    return (f32x4)a;
}
