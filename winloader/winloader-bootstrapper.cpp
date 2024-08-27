#include <windows.h>
#include "winloader-bootstrapper.h"
#include "winloader-environment.h"
#include "winloader-sha256.h"
#include "winloader-mem-strings.h"
#include "winloader-bootstrap.h"
#include "intrin.h"

#ifndef TO_LOWERCASE
#define TO_LOWERCASE(out, c1) (out = (c1 <= 'Z' && c1 >= 'A') ? c1 = (c1 - 'A') + 'a': c1)
#endif

#define WINLOADER_MAX_ALLOWED_FORWARDED_NAME 512

#pragma optimize("", off)
winloader::Bootstrapper::Bootstrapper() {
#if defined(ENVIRONMENT64)
    unsigned long long s1 = abs(0x452);
    unsigned long long s2 = abs(0x432);
    this->peb = (PPEB) __readgsqword(s1 ^ s2);
#else
    unsigned long s1 = abs(0x372);
    unsigned long s2 = abs(0x342);
    this->peb = (PPEB) __readfsdword(0x30);
#endif
}
#pragma optimize("", on)

void *winloader::Bootstrapper::getModuleByName(WCHAR *moduleName) {
    PPEB_LDR_DATA ldr = this->peb->Ldr;
    LIST_ENTRY moduleListHead = ldr->InLoadOrderModuleList;

    auto currentModule = reinterpret_cast<LDR_DATA_TABLE_ENTRY *>(moduleListHead.Flink);

    while (currentModule && currentModule->BaseAddress) {
        if (currentModule->BaseDllName.Buffer == nullptr) {
            currentModule = reinterpret_cast<LDR_DATA_TABLE_ENTRY *>(currentModule->InLoadOrderModuleList.Flink);
            continue;
        };
        auto currentModuleName = currentModule->BaseDllName.Buffer;
        for (size_t i = 0; true; i++) {
            WCHAR c1, c2;
            TO_LOWERCASE(c1, moduleName[i]);
            TO_LOWERCASE(c2, currentModuleName[i]);
            if (c1 != c2) break;
            if (c2 == 0) return currentModule->BaseAddress;
        }
        currentModule = reinterpret_cast<LDR_DATA_TABLE_ENTRY *>(currentModule->InLoadOrderModuleList.Flink);
    }

    return nullptr;
}

PIMAGE_NT_HEADERS winloader::Bootstrapper::getNtHeaders(LPVOID module) {
    auto castedModule = static_cast<char *>(module);
    auto dosHeader = reinterpret_cast<IMAGE_DOS_HEADER *>(module);
    if (dosHeader->e_magic != IMAGE_DOS_SIGNATURE) return nullptr;
    auto ntHeaders = reinterpret_cast<IMAGE_NT_HEADERS *>(castedModule + dosHeader->e_lfanew);
    if (ntHeaders->Signature != IMAGE_NT_SIGNATURE) return nullptr;
    return ntHeaders;
}

void *winloader::Bootstrapper::getFunctionByName(LPVOID module, const char *functionName) {
    auto castedModule = static_cast<char *>(module);
    auto ntHeaders = winloader::Bootstrapper::getNtHeaders(module);
    if (!ntHeaders) return nullptr;
    auto exportsDirectory = &(ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT]);
    auto exportsVirtualAddress = exportsDirectory->VirtualAddress;
    auto exports = reinterpret_cast<IMAGE_EXPORT_DIRECTORY *> (exportsVirtualAddress + castedModule);
    auto nameCount = exports->NumberOfNames;

    auto functionAddressList = reinterpret_cast<DWORD *>(castedModule + exports->AddressOfFunctions);
    auto functionNameList = reinterpret_cast<DWORD *>(castedModule + exports->AddressOfNames);
    auto namedOrdinalList = reinterpret_cast<WORD *>(castedModule + exports->AddressOfNameOrdinals);

    for (unsigned long i = 0; i < nameCount; i++) {
        auto nameRVA = functionNameList[i];
        auto nameIndex = namedOrdinalList[i];
        auto addressRVA = functionAddressList[nameIndex];

        auto currentName = castedModule + nameRVA;

        for (size_t k = 0; true; k++) {
            if (currentName[k] != functionName[k]) break;
            if (functionName[k] == 0) {
                return winloader::Bootstrapper::resolveExportRVA(module, addressRVA);
            }
        }
    }

    return nullptr;
}

void *winloader::Bootstrapper::getFunctionByHash(LPVOID module, const char *hash) {
    auto castedModule = static_cast<char *>(module);
    auto ntHeaders = winloader::Bootstrapper::getNtHeaders(module);
    if (!ntHeaders) return nullptr;
    auto exportsDirectory = &(ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT]);
    auto exportsVirtualAddress = exportsDirectory->VirtualAddress;
    auto exports = reinterpret_cast<IMAGE_EXPORT_DIRECTORY *> (exportsVirtualAddress + castedModule);
    auto nameCount = exports->NumberOfNames;

    auto functionAddressList = reinterpret_cast<DWORD *>(castedModule + exports->AddressOfFunctions);
    auto functionNameList = reinterpret_cast<DWORD *>(castedModule + exports->AddressOfNames);
    auto namedOrdinalList = reinterpret_cast<WORD *>(castedModule + exports->AddressOfNameOrdinals);

    char digest[32];
    for (unsigned long i = 0; i < nameCount; i++) {
        auto nameRVA = functionNameList[i];
        auto nameIndex = namedOrdinalList[i];
        auto addressRVA = functionAddressList[nameIndex];
        auto currentName = castedModule + nameRVA;
        winloader::sha256(currentName, reinterpret_cast<char *>(&digest));
        if (!winloader::memcmp(&digest, hash, 32)) {
            return winloader::Bootstrapper::resolveExportRVA(module, addressRVA);
        }
    }

    return nullptr;
}

// Credits: https://github.com/arbiter34/GetProcAddress/blob/master/GetProcAddress/GetProcAddress.cpp
void *winloader::Bootstrapper::resolveExportRVA(LPVOID module, unsigned long long rva) {
    auto casted_module = static_cast<char *>(module);
    auto ntHeaders = winloader::Bootstrapper::getNtHeaders(module);
    if (!ntHeaders) return nullptr;
    auto exportsDirectory = &ntHeaders->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_EXPORT];
    auto directoryAddress = exportsDirectory->VirtualAddress;
    auto directorySize = exportsDirectory->Size;
    auto va = casted_module + rva;
    // If function is not forwarded, the RVA is located outside the import directory.
    if (rva < directoryAddress || rva >= directoryAddress + directorySize) {
        return reinterpret_cast<void *>(va);
    }
    auto forward_string = va;
    char forwarded_dll[WINLOADER_MAX_ALLOWED_FORWARDED_NAME];
    char forwarded_function[WINLOADER_MAX_ALLOWED_FORWARDED_NAME];

    auto raw_forwarded_dll = forward_string;
    size_t forwarded_dll_length;
    for (forwarded_dll_length = 0; raw_forwarded_dll[forwarded_dll_length] != '.'; forwarded_dll_length++) {}

    auto raw_forwarded_function = raw_forwarded_dll + forwarded_dll_length + 1;
    size_t forwarded_function_length = winloader::strlen(raw_forwarded_function);


    winloader::strcpy_sl(forwarded_dll, raw_forwarded_dll, forwarded_dll_length, WINLOADER_MAX_ALLOWED_FORWARDED_NAME);
    winloader::strcpy_sl(forwarded_function, raw_forwarded_function, forwarded_function_length,
                         WINLOADER_MAX_ALLOWED_FORWARDED_NAME);

    typedef struct $$STRINGTYPE$$dll_ext {
        unsigned __int32 m0;
        unsigned __int8 m1;
    } $$STRINGTYPE$$dll_ext;

    $$STRINGTYPE$$dll_ext dll_ext;
    dll_ext.m0 = 1819042862U;
    dll_ext.m1 = 0U;

    winloader::strcat_s(forwarded_dll, (char *) &dll_ext, WINLOADER_MAX_ALLOWED_FORWARDED_NAME);
    return winloader::load_function(forwarded_dll, forwarded_function);
}


void winloader::Bootstrapper::resumeExecution(DWORD oldEntryPoint) {
    auto ptr = (char *) peb->ImageBaseAddress + oldEntryPoint;
    auto castedPtr = reinterpret_cast<void (*)()>(ptr);
    castedPtr();
};

void *winloader::Bootstrapper::getCurrentImage() {
    return peb->ImageBaseAddress;
}