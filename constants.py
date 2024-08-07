import os

ROOT_PATH = os.path.dirname(__file__)

HEADER_LOCATIONS = [
    "C:\\Program Files (x86)\\Windows Kits\\10\\Include\\10.0.26100.0",
    "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.39.33519\\include"
]

# These headers are disabled because they are from incompatible Windows SDKs, such as the Windows Driver Kit.
DISABLED_HEADERS = [
    "ntifs.h",
    "fltkernel.h",
]
