import os
import fnmatch

import cxxheaderparser.simple
from pcpp import Preprocessor


def scan_header_paths_recursive(paths: list[str]):
    header_locations = []
    for parent_dir, file in scan_header_files_recursive(paths):
        header_locations.append(parent_dir)
    return header_locations


def scan_header_files_recursive(paths: list[str]):
    for path in paths:
        for parent_dir, dirs, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, "*.h") or fnmatch.fnmatch(file, "*.hpp") or fnmatch.fnmatch(file, "*.cuh"):
                    yield parent_dir, file


class EvalPreprocessor(Preprocessor):
    FUNCTION_REGION_COMMENT = ("/* $$$$$$$$$$$$$$$$$$$$$$$$$!WINDOWS_API_DATABASE_EVALUATED_FUNCTION_REGION"
                               "!$$$$$$$$$$$$$$$$$$$$$$$$$ */")

    def __init__(self, header_paths, *, initial_lines=None):
        super().__init__()
        self.initial_lines = "\n".join(initial_lines or [])
        self.line_directive = None
        for header_path in header_paths:
            self.add_path(header_path)

    def on_comment(self, comment):
        if comment.value == EvalPreprocessor.FUNCTION_REGION_COMMENT:
            return comment

    def evaluate_header(self, include_files, *, function_encoding="ascii"):
        includes = "\n".join(f'#include "{file}"' for file in include_files)

        if function_encoding == "unicode":
            def_unicode = "#define UNICODE"
        else:
            def_unicode = ""

        raw_content = f"""\
{self.initial_lines}

{def_unicode}

{EvalPreprocessor.FUNCTION_REGION_COMMENT}

{includes}

{EvalPreprocessor.FUNCTION_REGION_COMMENT}
        """

        self.parse(raw_content)
        tokens = []
        merge_to_eval = 0
        while True:
            token = self.token()
            if not token:
                break
            if token.type == "CPP_COMMENT1":
                merge_to_eval += 1
                continue
            if merge_to_eval == 1:
                tokens.append(token.value)
        return "".join(tokens)

    def evaluate(self, content, *, function_encoding="ascii", include_files):
        includes = "\n".join(f'#include "{file}"' for file in include_files)

        if function_encoding == "unicode":
            def_unicode = "#define UNICODE"
        else:
            def_unicode = ""

        raw_content = f"""\
{self.initial_lines}

{def_unicode}

{includes}

{EvalPreprocessor.FUNCTION_REGION_COMMENT}

{content}
"""
        self.parse(raw_content)
        tokens = []
        merge_to_eval = False
        while True:
            token = self.token()
            if not token:
                break
            if token.type == "CPP_COMMENT1":
                merge_to_eval = True
                continue
            if merge_to_eval:
                tokens.append(token.value)
        return "".join(tokens)


if __name__ == '__main__':
    paths = scan_header_paths_recursive([
        "C:\\Program Files (x86)\\Windows Kits\\10\\Include",
        "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.39.33519\\include"
    ])
    initial_lines = [
        "#define __cplusplus 1",
        "#define _WIN64 1",
        "#define _AMD64_ 1",
        "#define _M_AMD64 1",
        "#define _M_X64 1",
        "#define _MSC_VER 1939",
        "#define _MSC_FULL_VER 193933519",
        "#define __DATE__ 01 30 2024",
        "#define __LINE__ 4",
        "#define __STDC__ 1",
        "#define _XM_SSE_INTRINSICS_ 1",
        "#define __INTRIN_H_ 1",
        "#define __export",
        "#include <minwindef.h>"
    ]
    preprocessor = EvalPreprocessor(paths, initial_lines=initial_lines)
    out = preprocessor.evaluate_header(["fileapi.h"], function_encoding="unicode")
    parsed = cxxheaderparser.simple.parse_string(out)

    for f in parsed.namespace.functions:
        print(f.name)
