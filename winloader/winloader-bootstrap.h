#pragma once
#include "windows.h"

namespace winloader {
    void bootstrap();
    void* load_function(char* library, char* function);
    void* load_function_by_hash(char* library, char* hash);

    inline decltype(LoadLibraryA)* $LoadLibraryA;
    inline decltype(GetProcAddress)* $GetProcAddress;
}