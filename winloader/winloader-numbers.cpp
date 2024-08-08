#include "winloader-numbers.h"

unsigned __int32 winloader::right_rotate(unsigned __int32 o, unsigned int count) {
    return (o << (32 - count)) | o >> count;
}

void winloader::byte_swap(char *c1, char *c2) {
    auto tmp = *c1;
    *c1 = *c2;
    *c2 = tmp;
}


unsigned __int64 winloader::endian_swap(unsigned __int64 input) {
    auto output = input;
    auto ptr = (char *) &output;
    byte_swap(&ptr[0], &ptr[7]);
    byte_swap(&ptr[1], &ptr[6]);
    byte_swap(&ptr[2], &ptr[5]);
    byte_swap(&ptr[3], &ptr[4]);
    return output;
}

unsigned __int32 winloader::endian_swap(unsigned __int32 input) {
    auto output = input;
    auto ptr = (char *) &output;
    byte_swap(&ptr[0], &ptr[3]);
    byte_swap(&ptr[1], &ptr[2]);
    return output;
}


size_t winloader::minimum_divisible_by(size_t dividend, size_t divisor) {
    if (!(dividend % divisor)) {
        return dividend;
    }
    return (dividend / divisor + 1) * divisor;
}

size_t winloader::min(size_t a1, size_t a2) {
    return a1 < a2 ? a1 : a2;
}