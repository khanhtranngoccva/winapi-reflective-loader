import fnmatch
import os
import sys
import clang.cindex
from tqdm import tqdm

import constants
from helpers import header_scanner
from helpers.lru import LRUCache

clang_cache_path = os.path.join(constants.ROOT_PATH, ".clang_cache", "headers")
os.makedirs(clang_cache_path, exist_ok=True)


def generate_all_builtin_signatures(*, cached=True):
    for (directory, file) in tqdm(list(header_scanner.scan_header_files_recursive(constants.HEADER_LOCATIONS))):
        header_file = file.lower()
        try:
            parse_builtin_header(header_file, cached=cached)
        except Exception as e:
            print(e, file=sys.stderr)


# A normal program would need up to 50 built-in headers.
lru_cache = LRUCache(capacity=50)


def parse_builtin_header(header_file, *, cached=True):
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
    header_content = f"""#define WINVER 0x0A00
#define _AMD64_ 1
#define _USER32_ 1
#include <cstdint>
#include <windef.h>
#include "{header_file}"
"""
    parsed = index.parse("evaluate.hpp", ["-Wall"], unsaved_files=[
        ("evaluate.hpp", header_content),
    ])
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

