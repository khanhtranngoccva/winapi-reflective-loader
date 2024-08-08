#include "windows.h"
#include "winloader-bootstrap.h"
#include "winloader-bootstrapper.h"

void winloader::bootstrap() {
    auto bootstrapper = winloader::Bootstrapper();
    auto module = bootstrapper.getModuleByName((wchar_t *) L"kernel32.dll");
    winloader::$LoadLibraryA = reinterpret_cast<decltype(LoadLibraryA) *>(bootstrapper.getFunctionByName(module,
                                                                                                         "LoadLibraryA"));
    winloader::$GetProcAddress = reinterpret_cast<decltype(GetProcAddress) *>(bootstrapper.getFunctionByName(module,
                                                                                                             "GetProcAddress"));
}

void *winloader::load_function(char *library, char *function) {
    if (!winloader::$LoadLibraryA || !winloader::$GetProcAddress) bootstrap();
    auto lib = winloader::$LoadLibraryA(library);
    auto proc = (void *) winloader::Bootstrapper::getFunctionByName(lib, function);
    return proc;
}

void *winloader::load_function_by_hash(char *library, char *hash) {
    if (!winloader::$LoadLibraryA || !winloader::$GetProcAddress) bootstrap();
    auto lib = winloader::$LoadLibraryA(library);
    auto proc = (void *) winloader::Bootstrapper::getFunctionByHash(lib, hash);
    return proc;
}
