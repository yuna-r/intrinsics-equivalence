/* Independent oracle for test_adversarial_models.py. Run on x86_64, or
 * explicitly under Rosetta on an Apple Silicon Mac. This is not POWER or
 * cross-host native conformance evidence. See ../BUG_HUNT.md.
 *
 * Usage: probe_sse2_nan f32|f64 OP LEFT_HEX RIGHT_HEX [ROUNDING]
 * OP also supports sqrt, cvt_i32, cvtt_i32, cvt_i64, cvtt_i64,
 * narrow (f64->f32), from_i32, and from_i64 (f64 only).
 * Prints the low result lane as an IEEE bit pattern. Runtime input and
 * strict FP compilation prevent compile-time NaN folding by the host.
 */
#include <emmintrin.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int parse_bits(const char *text, uint64_t *bits)
{
    char *end;
    errno = 0;
    if (text[0] == '-' || text[0] == '\0') return 0;
    *bits = strtoull(text, &end, 16);
    return errno == 0 && end != text && *end == '\0';
}

int main(int argc, char **argv)
{
    uint64_t left, right;
    int operation;
    unsigned rounding = 0;
    if ((argc != 5 && argc != 6) || !parse_bits(argv[3], &left) || !parse_bits(argv[4], &right)) {
        fprintf(stderr, "usage: %s f32|f64 OP LEFT_HEX RIGHT_HEX [ROUNDING]\n", argv[0]);
        return 2;
    }
    if (!strcmp(argv[2], "add")) operation = 0;
    else if (!strcmp(argv[2], "sub")) operation = 1;
    else if (!strcmp(argv[2], "mul")) operation = 2;
    else if (!strcmp(argv[2], "div")) operation = 3;
    else if (!strcmp(argv[2], "sqrt")) operation = 4;
    else if (!strcmp(argv[2], "cvt_i32")) operation = 5;
    else if (!strcmp(argv[2], "cvtt_i32")) operation = 6;
    else if (!strcmp(argv[2], "cvt_i64")) operation = 7;
    else if (!strcmp(argv[2], "cvtt_i64")) operation = 8;
    else if (!strcmp(argv[2], "narrow")) operation = 9;
    else if (!strcmp(argv[2], "from_i32")) operation = 10;
    else if (!strcmp(argv[2], "from_i64")) operation = 11;
    else return 2;

    if (argc == 6) {
        if (!strcmp(argv[5], "toward_negative")) rounding = 0x2000;
        else if (!strcmp(argv[5], "toward_positive")) rounding = 0x4000;
        else if (!strcmp(argv[5], "toward_zero")) rounding = 0x6000;
        else if (strcmp(argv[5], "nearest_even")) return 2;
    }

    /* All exceptions masked, nearest-even, FTZ and DAZ disabled. */
    _mm_setcsr(0x1F80 | rounding);
    if (!strcmp(argv[1], "f32")) {
        uint32_t a_bits[4], b_bits[4], output[4];
        __m128 a, b, result;
        if (left > UINT32_MAX || right > UINT32_MAX) return 2;
        for (int lane = 0; lane < 4; ++lane) {
            a_bits[lane] = (uint32_t)left;
            b_bits[lane] = (uint32_t)right;
        }
        memcpy(&a, a_bits, sizeof(a));
        memcpy(&b, b_bits, sizeof(b));
        if (operation == 5 || operation == 6) {
            int value = operation == 5 ? _mm_cvtss_si32(a) : _mm_cvttss_si32(a);
            printf("0x%08" PRIx32 "\n", (uint32_t)value);
            return 0;
        }
        if (operation == 7 || operation == 8 || operation == 9 || operation == 11) return 2;
        switch (operation) {
        case 0: result = _mm_add_ps(a, b); break;
        case 1: result = _mm_sub_ps(a, b); break;
        case 2: result = _mm_mul_ps(a, b); break;
        case 3: result = _mm_div_ps(a, b); break;
        case 4: result = _mm_sqrt_ps(a); break;
        default: {
            int value;
            memcpy(&value, a_bits, sizeof(value));
            result = _mm_cvtsi32_ss(_mm_setzero_ps(), value);
            break;
        }
        }
        memcpy(output, &result, sizeof(output));
        printf("0x%08" PRIx32 "\n", output[0]);
    } else if (!strcmp(argv[1], "f64")) {
        uint64_t a_bits[2] = {left, left}, b_bits[2] = {right, right}, output[2];
        __m128d a, b, result;
        memcpy(&a, a_bits, sizeof(a));
        memcpy(&b, b_bits, sizeof(b));
        if (operation == 5 || operation == 6) {
            int value = operation == 5 ? _mm_cvtsd_si32(a) : _mm_cvttsd_si32(a);
            printf("0x%08" PRIx32 "\n", (uint32_t)value);
            return 0;
        }
        if (operation == 7 || operation == 8) {
            long long value = operation == 7 ? _mm_cvtsd_si64(a) : _mm_cvttsd_si64(a);
            printf("0x%016" PRIx64 "\n", (uint64_t)value);
            return 0;
        }
        if (operation == 9) {
            uint32_t narrow[4];
            __m128 result32 = _mm_cvtpd_ps(a);
            memcpy(narrow, &result32, sizeof(narrow));
            printf("0x%08" PRIx32 "\n", narrow[0]);
            return 0;
        }
        switch (operation) {
        case 0: result = _mm_add_pd(a, b); break;
        case 1: result = _mm_sub_pd(a, b); break;
        case 2: result = _mm_mul_pd(a, b); break;
        case 3: result = _mm_div_pd(a, b); break;
        case 4: result = _mm_sqrt_pd(a); break;
        case 10: {
            uint32_t bits = (uint32_t)left;
            int value;
            memcpy(&value, &bits, sizeof(value));
            result = _mm_cvtsi32_sd(_mm_setzero_pd(), value);
            break;
        }
        default: {
            long long value;
            memcpy(&value, &left, sizeof(value));
            result = _mm_cvtsi64_sd(_mm_setzero_pd(), value);
            break;
        }
        }
        memcpy(output, &result, sizeof(output));
        printf("0x%016" PRIx64 "\n", output[0]);
    } else return 2;
    return 0;
}
