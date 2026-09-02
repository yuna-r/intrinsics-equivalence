#ifndef IOITF_OFFICIAL_SHORTCUTS_H
#define IOITF_OFFICIAL_SHORTCUTS_H

/* Keep the symbol visible; hide only the five-line C ceremony. */
#define IOITF_BINARY(RESULT, ARGUMENT, NAME, ...) \
    RESULT NAME(ARGUMENT a, ARGUMENT b)           \
    {                                              \
        return (__VA_ARGS__);                      \
    }

#define IOITF_UNARY(RESULT, ARGUMENT, NAME, ...) \
    RESULT NAME(ARGUMENT a)                       \
    {                                              \
        return (__VA_ARGS__);                      \
    }

#endif
