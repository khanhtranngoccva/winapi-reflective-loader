import json
import os
import pprint
import shutil
import sys
import argparse
import traceback

from tqdm import tqdm

import constants
import helpers.errors
from generator import preparation, builder
from helpers import arguments
from helpers.pe import analyze_imports


def should_generate_signature_code(name, *_, imports):
    if imports is None:
        return True
    for executable_import in imports:
        if name == executable_import["name"]:
            return True
    return False


def pop_executable_imports(name, *_, imports):
    if imports is None:
        return
    for executable_import in imports:
        if name == executable_import["name"]:
            imports.remove(executable_import)
            return


def generate_loaders(database, opts):
    def _get_first_header(sig):
        if len(sig.get("headers")) > 0:
            return sig["headers"][0]
        else:
            return ""

    database.sort(key=_get_first_header)

    structure = {}

    processed_names = set()

    for definition in tqdm(database):
        try:
            preparation.normalize(definition)
            sigs = preparation.get_signatures(definition)
            for signature in sigs:
                if not should_generate_signature_code(
                        signature["signature_name"],
                        imports=opts.get("executable_imports")
                ):
                    continue
                match_result = builder.build_loader_from_signature(signature)
                if match_result.loader is None:
                    continue
                if (match_result.loader.mangled_name or match_result.loader.name) in processed_names:
                    continue
                header = match_result.header
                function_data = structure.get(header)
                if function_data is None:
                    function_data = {
                        "includes": set(),
                        "headers": [],
                        "implementations": [],
                    }
                    structure[header] = function_data
                includes = function_data.get("includes")
                headers = function_data.get("headers")
                implementations = function_data.get("implementations")
                includes.add(match_result.header)
                for extra_include in match_result.loader.extra_includes:
                    includes.add(extra_include)
                headers.append(match_result.loader.header)
                implementations.append(match_result.loader.implementation)
                processed_names.add(match_result.loader.mangled_name or match_result.loader.name)
                pop_executable_imports(
                    signature["signature_name"], imports=opts.get("executable_imports")
                )
        except Exception as e:
            e.definition = definition
            helpers.errors.save_to_disk(e)

    output = {}
    for original_header_name, function_data in structure.items():
        if len(opts["enables"]) > 0 and opts["enables"].count(original_header_name) == 0:
            continue
        elif opts["disables"].count(original_header_name) > 0:
            continue
        _header_name = os.path.splitext(original_header_name)[0]
        new_store_name = f"$$LOADER$${_header_name}"
        new_impl_name = new_store_name + ".cpp"
        new_header_name = new_store_name + ".h"
        if opts.get("header_prefix"):
            new_impl_include = os.path.join(opts["header_prefix"], new_header_name).replace("\\", "/")
        else:
            new_impl_include = new_header_name

        includes_list = list(f"#include \"{include}\"" for include in function_data['includes'])

        extra_local_includes = reversed(opts.get("extra_local_includes", {}).get(original_header_name, []))
        for extra_local_include in extra_local_includes:
            includes_list.insert(0, f"#include \"{extra_local_include}\"")

        for extra_global_include in reversed(opts.get("extra_global_includes", [])):
            includes_list.insert(0, f"#include \"{extra_global_include}\"")

        includes_string = "\n".join(includes_list)
        headers_string = "\n".join(function_data['headers'])
        implementations_string = "\n".join(function_data['implementations'])
        header_file_string = f"""#pragma once
{includes_string}

{headers_string}
"""

        implementation_file_string = f"""#include "winloader-bootstrap.h"
#include "winloader-numbers.h"
#include "winloader-mem-strings.h"
#include "{new_impl_include}"

{implementations_string}"""

        output[original_header_name] = {
            "include": f'#include "{new_impl_include}"',
            "impl_name": new_impl_name,
            "header_name": new_header_name,
            "header": header_file_string,
            "implementation": implementation_file_string,
        }

    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", dest="input", required=False,
                        default=os.path.join(constants.ROOT_PATH, "database"), help="Input database")
    parser.add_argument("-oh", "--output-header", dest="output_header", required=True, help="Header output directory")
    parser.add_argument("-oi", "--output-implementation", dest="output_implementation", required=True,
                        help="Implementation output directory")
    parser.add_argument("-os", "--output-summary", dest="output_summary", required=True,
                        help="Summary header directory for direct use")
    parser.add_argument("-hp", "--header-prefix", dest="header_prefix", type=bool, default=False,
                        help="Enable header prefix")
    parser.add_argument("-exg", "--extra-global-include", dest="extra_global_includes", type=str, action="append",
                        default=None,
                        help="Header include files")
    parser.add_argument("-exd", "--exclude-dll", dest="exclude_dlls", type=str, action="append", default=[],
                        help="Disable DLLs that are not available on the system. Helps resolve conflicts.")
    g1 = parser.add_mutually_exclusive_group()
    g1.add_argument("-d", "--disable", dest="disables", type=str, action="append", default=None,
                    help="Disable headers to increase compatibility")
    g1.add_argument("-e", "--enable", dest="enables", type=str, action="append", default=None,
                    help="Enable selected headers and disable everything else")
    g1.add_argument("-exe", "--executable", dest="executable", type=str, default=None,
                    help="Automatically pick function definitions based on executable")
    parser.add_argument("-exl", "--extra-local-include", dest="extra_local_includes", type=str, action="append",
                        metavar="KEY=VALUE", default=None, help="Add an extra include directive to one library")

    args = parser.parse_args()

    database = []
    for root, dirs, files in os.walk(args.input):
        for file in files:
            if os.path.splitext(file)[1] == ".json":
                with open(os.path.join(root, file)) as f:
                    try:
                        database.append(json.load(f))
                    except json.decoder.JSONDecodeError:
                        print("Could not parse file: {}".format(os.path.join(root, file)), file=sys.stderr)

    header_prefix = os.path.basename(args.output_header) if args.header_prefix else None
    extra_global_includes = args.extra_global_includes or []
    disables = args.disables or []
    enables = args.enables or []
    extra_local_includes = arguments.parse_metavar_array(args.extra_local_includes or [])
    executable_imports = None
    exclude_dlls = []

    if args.executable:
        executable_imports = []
        for import_data in analyze_imports(args.executable):
            executable_imports.append(import_data)

    if args.exclude_dlls:
        for dll in args.exclude_dlls:
            exclude_dlls.append(dll.lower())

    parsed = generate_loaders(database, {
        "header_prefix": header_prefix,
        "extra_global_includes": extra_global_includes,
        "disables": disables,
        "enables": enables,
        "executable_imports": executable_imports,
        "extra_local_includes": extra_local_includes,
        "exclude_dlls": exclude_dlls,
    })

    for _import in executable_imports:
        print("Unprocessed import {}".format(_import), file=sys.stderr)
    if executable_imports:
        print("Missing {} executable imports".format(len(executable_imports)))

    shutil.rmtree(args.output_header, ignore_errors=True)
    os.makedirs(args.output_header, exist_ok=True)
    shutil.rmtree(args.output_implementation, ignore_errors=True)
    os.makedirs(args.output_implementation, exist_ok=True)

    includes = []
    for _, data in parsed.items():
        includes.append(data["include"])
        impl_path = os.path.join(args.output_implementation, data["impl_name"])
        header_path = os.path.join(args.output_header, data["header_name"])
        with open(impl_path, "w") as f:
            f.write(data["implementation"])
        with open(header_path, "w") as f:
            f.write(data["header"])
        shutil.copytree(os.path.join(constants.ROOT_PATH, "winloader"), args.output_implementation, False,
                        ignore=shutil.ignore_patterns(""),
                        dirs_exist_ok=True)

    includes_string = "\n".join(includes)
    includes_string_wrapped = f"""#pragma once

{includes_string}
"""
    with open(args.output_summary, "w") as f:
        f.write(includes_string_wrapped)
