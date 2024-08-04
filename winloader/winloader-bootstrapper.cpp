#include <windows.h>
#include "winloader-bootstrapper.h"
#include "winloader-environment.h"
#include "intrin.h"

#ifndef TO_LOWERCASE
#define TO_LOWERCASE(out, c1) (out = (c1 <= 'Z' && c1 >= 'A') ? c1 = (c1 - 'A') + 'a': c1)
#endif

Bootstrapper::Bootstrapper() {
#if defined(ENVIRONMENT64)
    this->peb = (PPEB) __readgsqword(0x60);
#else
    this->peb = (PPEB) __readfsdword(0x30);
#endif
}

void *Bootstrapper::getModuleByName(WCHAR *moduleName) {
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

void *Bootstrapper::getFunctionByName(LPVOID module, const char *functionName) {
    auto castedModule = static_cast<char *>(module);
    auto dosHeader = reinterpret_cast<IMAGE_DOS_HEADER *>(module);
    if (dosHeader->e_magic != IMAGE_DOS_SIGNATURE) return nullptr;
    auto ntHeaders = reinterpret_cast<IMAGE_NT_HEADERS *>(castedModule + dosHeader->e_lfanew);
    if (ntHeaders->Signature != IMAGE_NT_SIGNATURE) return nullptr;
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
            if (functionName[k] == 0) return castedModule + addressRVA;
        }
    }

    return nullptr;
}

void Bootstrapper::resumeExecution(DWORD oldEntryPoint) {
    auto ptr = (char *) peb->ImageBaseAddress + oldEntryPoint;
    auto castedPtr = reinterpret_cast<void (*)()>(ptr);
    castedPtr();
};

void *Bootstrapper::getCurrentImage() {
    return peb->ImageBaseAddress;
}