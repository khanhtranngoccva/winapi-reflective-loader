#pragma once

#include <cstdint>

namespace winloader {
    size_t strlen(const char *str);

    void memcpy(void *dest, const void *source, size_t bytes);

    void memset(void *dest, char value, size_t bytes);

    char memcmp(const void *ptr1, const void *ptr2, size_t bytes);

    void strcpy_s(char *dest, const char *source, size_t max_bytes);

    void strcat_s(char *dest, const char *source, size_t max_bytes);

    void strcpy_sl(char *dest, const char *source, size_t length, size_t max_bytes);

    void strcpy(char *dest, const char *source);
};