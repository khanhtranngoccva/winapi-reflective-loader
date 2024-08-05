import concurrent.futures
import json
import os.path
import shutil
import sys

import clang.cindex
from tqdm import tqdm
import constants
import helpers.errors
from helpers import header_scanner, futures

clang_cache_alias_path = os.path.join(constants.ROOT_PATH, ".clang_cache", "aliases")
os.makedirs(clang_cache_alias_path, exist_ok=True)


def search_all_define_lines(header_path, *, _visited=None):
    if not _visited:
        _visited = set()
    defines = []
    try:
        with open(header_path, encoding="utf-8") as f:
            lines = f.readlines()
            full_path = header_path.lower()
    except FileNotFoundError as e:
        for (directory, file) in header_scanner.scan_header_files_recursive(constants.HEADER_LOCATIONS):
            if file.lower() == header_path.lower():
                full_path = os.path.join(directory, file).lower()
                break
        else:
            raise e
        with open(full_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    if full_path in _visited:
        return []
    _visited.add(full_path)
    cur_define = []
    for line in lines:
        line = line.lstrip()
        if line.startswith("#define") or cur_define:
            cur_define.append(line)
        if not line.endswith("\\\n") and cur_define:
            defines.append(cur_define)
            cur_define = []
        if not cur_define and line.startswith("#include"):
            data = line.strip().split(" ")
            if len(data) < 2:
                raise helpers.errors.DefineSearchError(full_path)
            fn = data[1]
            basic_check = False
            if fn[0] == "<" and fn[-1] == ">" and not fn[1:-1].count("<") and not fn[1:-1].count(">"):
                basic_check = True
            elif fn[0] == "\"" and fn[-1] == "\"" and not fn[1:-1].count("\""):
                basic_check = True
            if not basic_check:
                raise helpers.errors.DefineSearchError(full_path)
            try:
                for define in search_all_define_lines(fn[1:-1], _visited=_visited):
                    defines.append(define)
            except FileNotFoundError:
                pass
    if cur_define:
        defines.append(cur_define)
    return defines


def get_all_macro_aliases(*, cached=True):
    if not cached:
        shutil.rmtree(clang_cache_alias_path, ignore_errors=True)
    with concurrent.futures.ThreadPoolExecutor(8) as executor:
        total = 0
        futures_list = []
        for (directory, file) in list(header_scanner.scan_header_files_recursive(constants.HEADER_LOCATIONS)):
            total += 1
            full_path = os.path.join(directory, file)
            futures_list.append(executor.submit(get_macro_aliases, full_path, cached=cached))

        with helpers.futures.interrupt_futures(futures_list):
            with tqdm(total=total) as progress_bar:
                for future in concurrent.futures.as_completed(futures_list):
                    try:
                        future.result()
                    except Exception as e:
                        print(e, file=sys.stderr)
                    progress_bar.update(1)


def get_macro_aliases(header_path, *_, cached=True):
    try:
        header_filename = os.path.splitext(os.path.basename(header_path))[0] + ".json"
        cache_alias_path_for_header = os.path.join(clang_cache_alias_path, header_filename)
        if cached:
            try:
                with open(cache_alias_path_for_header, "r") as f:
                    data = json.load(f)
                return data
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                pass
        # Collect all #defines, including defines with continuation backslashes, regardless of conditions.
        defines = search_all_define_lines(header_path)
        header_content = "".join("".join(line for line in define) for define in defines)
        header_content = "#include <minwindef.h>\n" + header_content
        index = clang.cindex.Index.create()
        parsed = index.parse("evaluate.h", [],
                             unsaved_files=[
                                 ["evaluate.h", header_content]
                             ],
                             options=clang.cindex.TranslationUnit.PARSE_SKIP_FUNCTION_BODIES |
                                     clang.cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
        cursor = parsed.cursor
        alias_mappings = {}
        for node in cursor.walk_preorder():
            if node.kind.name == "MACRO_DEFINITION":
                tokens = []
                for token in node.get_tokens():
                    tokens.append(token.spelling)
                if len(tokens) != 2:
                    continue
                alias_mappings.setdefault(tokens[0], []).append(tokens[1])
        # Deduplicate run
        for k, v in alias_mappings.items():
            alias_mappings[k] = list(set(v))
        with open(cache_alias_path_for_header, "w") as f:
            json.dump(alias_mappings, f, indent=2)
        return alias_mappings
    except Exception as e:
        raise helpers.errors.AliasCollectionError(header_path, e)


if __name__ == '__main__':
    get_all_macro_aliases(cached=False)
