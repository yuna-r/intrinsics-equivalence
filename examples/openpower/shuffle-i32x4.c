#include <altivec.h>

typedef __vector unsigned int example_i32x4;

example_i32x4 openpower_example_reverse_i32x4(example_i32x4 value)
{
    return (example_i32x4){value[3], value[2], value[1], value[0]};
}
