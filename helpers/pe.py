import pefile


def analyze_imports(path: str):
    pe = pefile.PE(path)

    results = []

    imp: pefile.ImportDescData
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for imp in pe.DIRECTORY_ENTRY_IMPORT:
            if not hasattr(imp, "dll"):
                continue
            if not hasattr(imp, "imports"):
                continue
            dll = imp.dll.decode("ascii")
            import_list: list[pefile.ImportData] = imp.imports
            for import_obj in import_list:
                if not hasattr(import_obj, "name"):
                    continue
                obj = {
                    "name": import_obj.name.decode("ascii"),
                    "dll": dll
                }
                results.append(obj)

    return results
