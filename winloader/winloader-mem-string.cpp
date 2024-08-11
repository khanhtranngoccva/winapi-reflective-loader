#include "winloader-mem-string.h"

size_t winloader::strlen(const char *str) {
    for (size_t i = 0;; i++) {
        if (str[i] == 0) return i;
    }
}

void winloader::memcpy(void *dest, const void *source, size_t bytes) {
    for (size_t i = 0; i < bytes; i++) {
        ((char *) dest)[i] = ((char *) source)[i];
    }
}

void winloader::strcpy_s(char *dest, const char *source, size_t max_bytes) {
    size_t i;
    for (i = 0; i < max_bytes - 1 && source[i]; i++) {
        ((char *) dest)[i] = ((char *) source)[i];
    }
    dest[i] = 0;
}

void winloader::strcpy_sl(char *dest, const char *source, size_t length, size_t max_bytes) {
    if (length >= max_bytes - 1) {
        length = max_bytes - 1;
    }
    size_t i;
    for (i = 0; i < length && source[i]; i++) {
        ((char *) dest)[i] = ((char *) source)[i];
    }
    dest[i] = 0;
}

void winloader::strcat_s(char *dest, const char *source, size_t max_bytes) {
    size_t i;
    auto cur_dest_length = winloader::strlen(dest);
    auto append_pointer = &dest[cur_dest_length];
    for (i = 0; i < max_bytes - 1 - cur_dest_length && source[i]; i++) {
        ((char *) append_pointer)[i] = ((char *) source)[i];
    }
    append_pointer[i] = 0;
}

void winloader::strcpy(char *dest, const char *source) {
    size_t i;
    for (i = 0; dest[i]; i++) {
        ((char *) dest)[i] = ((char *) source)[i];
    }
    dest[i] = 0;
}

char winloader::memcmp(const void *ptr1, const void *ptr2, size_t bytes) {
    auto _ptr1 = (char *) ptr1;
    auto _ptr2 = (char *) ptr2;
    for (size_t i = 0; i < bytes; i++) {
        auto diff = _ptr1[i] - _ptr2[i];
        if (diff) return (char) diff;
    }
    return 0;
}


void winloader::memset(void *dest, char value, size_t bytes) {
    for (size_t i = 0; i < bytes; i++) {
        ((char *) dest)[i] = value;
    }
}