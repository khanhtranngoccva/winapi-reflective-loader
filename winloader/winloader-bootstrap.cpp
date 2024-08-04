#include "windows.h"
#include "winloader-bootstrap.h"
#include "winloader-bootstrapper.h"

void bootstrap() {
    auto bootstrapper = Bootstrapper();
    auto module = bootstrapper.getModuleByName((wchar_t *) L"kernel32.dll");
    $LoadLibraryA = reinterpret_cast<decltype(LoadLibraryA) *>(bootstrapper.getFunctionByName(module, "LoadLibraryA"));
    $GetProcAddress = reinterpret_cast<decltype(GetProcAddress) *>(bootstrapper.getFunctionByName(module,"GetProcAddress"));
}

void *load_function(char *library, char *function) {
    if (!$LoadLibraryA || $GetProcAddress) bootstrap();
    auto lib = $LoadLibraryA(library);
    auto proc = (void *) $GetProcAddress(lib, function);
    return proc;
}