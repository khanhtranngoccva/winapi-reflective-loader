import fnmatch
import os
import sys
import clang.cindex
from tqdm import tqdm

import constants
from helpers.lru import LRUCache

HEADER_LOCATIONS = [
    "C:\\Program Files (x86)\\Windows Kits\\10\\Include",
    "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.39.33519\\include"
]

clang_cache_path = os.path.join(constants.ROOT_PATH, ".clang_cache")
os.makedirs(clang_cache_path, exist_ok=True)

def scan_header_files_recursive(paths: list[str]):
    for path in paths:
        for parent_dir, dirs, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, "*.h") or fnmatch.fnmatch(file, "*.hpp") or fnmatch.fnmatch(file, "*.cuh"):
                    yield parent_dir, file


def generate_all_builtin_signatures(*, cached=True):
    for (directory, file) in tqdm(list(scan_header_files_recursive(HEADER_LOCATIONS))):
        header_file = file.lower()
        try:
            clang_parse_builtin_header(header_file, cached=cached)
        except Exception as e:
            print(e, file=sys.stderr)


# A normal program would need up to 50 built-in headers.
lru_cache = LRUCache(capacity=50)


def clang_parse_builtin_header(header_file, *, cached=True):
    index = clang.cindex.Index.create()
    cache_path = os.path.join(clang_cache_path, header_file + ".cache")
    if cached:
        try:
            parsed = lru_cache.get(header_file)
            return parsed
        except KeyError:
            pass
        try:
            parsed = index.read(cache_path)
            lru_cache.put(header_file, parsed)
            return parsed
        except clang.cindex.TranslationUnitLoadError:
            pass

    # If cache is not found, start parsing
    header_content = f"""#include <minwindef.h>
#include "{header_file}"
"""
    parsed = index.parse("evaluate.h", ["-Wall"], unsaved_files=[
        ("evaluate.h", header_content),
    ], options=clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES)
    parsed.save(cache_path)
    lru_cache.put(header_file, parsed)
    return parsed


def dump_node(node, indent):
    if node.kind.name == "FUNCTION_DECL":
        print(node.is_definition())
    # print(' ' * indent, node.kind, node.spelling)
    for i in node.get_children():
        dump_node(i, indent + 2)


if __name__ == '__main__':
    generate_all_builtin_signatures(cached=False)