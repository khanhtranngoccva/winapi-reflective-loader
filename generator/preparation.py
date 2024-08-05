import copy
import sys

import helpers.signature.alias
import helpers.errors


def normalize(definition):
    def stage1():
        attributes_needed = ["name", "code", "headers", "dlls", "url"]
        attributes_missing = []
        for attribute in attributes_needed:
            if attribute not in definition or definition[attribute] is None:
                attributes_missing.append(attribute)
        if attributes_missing:
            raise AttributeError(
                f"Definition {definition.get('name')} missing attributes for function definition: {', '.join(attributes_missing)}")

    stage1()
    for i, v in enumerate(definition["headers"]):
        definition["headers"][i] = v.lower()
    for i, v in enumerate(definition["dlls"]):
        definition["dlls"][i] = v.lower()


def get_signatures(definition, *, cached=True):
    name = definition["name"]
    headers = definition["headers"]

    signature_names = set()

    # Search for macro aliases
    for header in headers:
        try:
            aliases = helpers.signature.alias.get_macro_aliases(header, cached=cached)
            if aliases.get(name):
                for real_signature_name in aliases[name]:
                    signature_names.add(real_signature_name)
        except helpers.errors.AliasCollectionError as e:
            if isinstance(e.nested_error, FileNotFoundError):
                pass
            else:
                raise e

    # Add itself if there is no macro alias
    if not len(signature_names):
        signature_names.add(name)

    return list({**definition, "signature_name": signature_name} for signature_name in signature_names)


if __name__ == '__main__':
    sig = get_signatures({
        "name": "SetCurrentDirectory",
        "code": "BOOL SetCurrentDirectory(\n  [in] LPCTSTR lpPathName\n);",
        "headers": [
            "windows.h",
            "winbase.h"
        ],
        "dlls": [
            "kernel32.dll"
        ],
        "url": "https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-setcurrentdirectory"
    }, cached=False)
    print(sig)
