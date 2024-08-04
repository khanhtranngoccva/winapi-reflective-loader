#include "windows.h"

void bootstrap();
void* load_function(char* library, char* function);

inline decltype(LoadLibraryA)* $LoadLibraryA;
inline decltype(GetProcAddress)* $GetProcAddress;