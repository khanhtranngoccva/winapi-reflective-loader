#pragma once

#include <cstdint>

namespace winloader {
    unsigned __int32 right_rotate(unsigned __int32 o, unsigned int count);

    void byte_swap(char *c1, char *c2);

    unsigned __int64 endian_swap(unsigned __int64 input);

    unsigned __int32 endian_swap(unsigned __int32 input);

    unsigned __int16 endian_swap(unsigned __int16 input);

    template <typename T>
    T n_xor(T input1, T input2) {
        return input1 ^ input2;
    }

    size_t minimum_divisible_by(size_t dividend, size_t divisor);

    size_t minimum(size_t a1, size_t a2);
};