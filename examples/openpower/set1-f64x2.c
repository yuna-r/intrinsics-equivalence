#include <altivec.h>

typedef __vector double example_f64x2;

example_f64x2 openpower_example_set1_f64x2(double value)
{
    return vec_splats(value);
}
