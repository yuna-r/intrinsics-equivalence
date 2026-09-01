#include <altivec.h>

typedef __vector double example_f64x2;

example_f64x2 openpower_example_add_f64x2(example_f64x2 a,
                                          example_f64x2 b)
{
    return vec_add(a, b);
}
