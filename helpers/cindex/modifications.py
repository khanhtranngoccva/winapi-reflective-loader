import ctypes

from clang import cindex

Cursor_is_function_inlined = cindex.conf.lib.clang_Cursor_isFunctionInlined
Cursor_is_function_inlined.argtypes = [cindex.Cursor]
Cursor_is_function_inlined.restype = ctypes.c_bool

# Cursor_function_has_body = cindex.conf.lib.clang_Cursor_isFunctionInlined
# Cursor_function_has_body.argtypes = [cindex.Cursor]
# Cursor_function_has_body.restype = ctypes.c_bool


def is_function_inlined(self):
    return Cursor_is_function_inlined(self)


cindex.Cursor.is_function_inlined = is_function_inlined
