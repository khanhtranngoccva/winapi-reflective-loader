import helpers.errors
from helpers.signature import processor
from clang import cindex
from construct_loader import construct_loader
from generator import types


def search_node_from_ast(tree: cindex.TranslationUnit, kind):
    root_cursor: cindex.Cursor = tree.cursor
    for node in root_cursor.walk_preorder():
        if node.kind.name == kind:
            yield node


def get_matching_function(signature, *, parse_code=False):
    for header in signature["headers"]:
        ast = processor.parse_builtin_header(header)
        for function_node in search_node_from_ast(ast, kind="FUNCTION_DECL"):
            if function_node.spelling == signature["signature_name"]:
                return types.FunctionMatch(function_node, header)
    raise helpers.errors.ParseError(signature)


def build_loader_from_signature(signature):
    result = get_matching_function(signature)
    loader = construct_loader(signature, result)
    result.loader = loader
    return result


if __name__ == '__main__':
    match = build_loader_from_signature({
        "code": "LRESULT DispatchMessage(\n  [in] const MSG *lpMsg\n);",
        "headers": [
            "winuser.h",
            "windows.h"
        ],
        "dlls": [
            "user32.dll"
        ],
        "url": "https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-dispatchmessagea",
        "name": "DispatchMessage",
        "signature_name": "DispatchMessageA"
    })
    print(match.loader.mangled_name)
