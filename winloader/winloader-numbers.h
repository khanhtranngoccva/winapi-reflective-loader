#pragma once

#include <cstdint>

namespace winloader {
    unsigned __int32 right_rotate(unsigned __int32 o, unsigned int count);

    void byte_swap(char *c1, char *c2);

    unsigned __int64 endian_swap(unsigned __int64 input);

    unsigned __int32 endian_swap(unsigned __int32 input);

    size_t minimum_divisible_by(size_t dividend, size_t divisor);

    size_t min(size_t a1, size_t a2);
}