import cxxheaderparser.errors
from cxxheaderparser.simple import parse_string
from helpers.preprocessor import EvalPreprocessor, scan_header_paths_recursive, scan_header_files_recursive
from clang import cindex

HEADER_LOCATIONS = [
    "C:\\Program Files (x86)\\Windows Kits\\10\\Include",
    "C:\\Program Files (x86)\\Microsoft Visual Studio\\2022\\BuildTools\\VC\\Tools\\MSVC\\14.39.33519\\include"
]

HEADER_PATHS = scan_header_paths_recursive(HEADER_LOCATIONS)

# This parse function is a nasty hack!!!
PARAM_MARKERS = [
    ["ref"],
    ["in", "ref"],
    ["in"],
    ["out"],
    ["in", "optional"],
    ["out", "optional"],
    ["in", "out"],
    ["in", "out", "optional"],
    ["optional"],
]
param_markers_strings = []
for param_marker in PARAM_MARKERS:
    param_markers_string = "[" + ", ".join(param_marker) + "]"
    param_markers_strings.append(param_markers_string)


def preprocess(header, *, function_encoding, include_file, preprocessor_initial_lines):
    preprocessor = EvalPreprocessor(HEADER_PATHS, initial_lines=preprocessor_initial_lines)
    return preprocessor.evaluate(header, include_files=[include_file], function_encoding=function_encoding)


def parse_function_header(header: str, *, include_file: str, function_encoding="ascii", force_preprocessor=False,
                          verbose=False, args):
    header = header.strip()
    for param_marker in param_markers_strings:
        header = header.replace(param_marker, "")

    force_preprocessor = force_preprocessor or (force_preprocessor or args.config
                                                .get("headers", {})
                                                .get(include_file.lower(), {})
                                                .get("preprocessor", {})
                                                .get("force", False))
    print("Preprocessor enabled:", force_preprocessor)

    parsed = ""

    def parse_with_preprocessor():
        nonlocal parsed
        preprocessed = preprocess(
            header,
            include_file=include_file,
            function_encoding=function_encoding,
            preprocessor_initial_lines=args.config.get("preprocessor", {}).get("initial_lines", [])
        )
        if verbose:
            print(preprocessed)
        parsed = parse_string(preprocessed)

    if force_preprocessor:
        parse_with_preprocessor()
    else:
        try:
            parsed = parse_string(header)
        except cxxheaderparser.errors.CxxParseError:
            parse_with_preprocessor()

    functions = parsed.namespace.functions
    function = functions[0]
    params = []
    for parameter in function.parameters:
        params.append({
            "name": parameter.name,
            "type": parameter.type.format()
        })
    output = {
        "name": function.name.format(),
        "ret": function.return_type.format(),
        "params": params,
        "inline": function.inline,
        "noexcept": bool(function.noexcept),
        "vararg": function.vararg,
    }
    return output
