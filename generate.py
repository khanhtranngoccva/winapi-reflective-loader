import json
import os
import pprint
import shutil
import sys
import argparse

from helpers import arguments
from helpers.pe import analyze_imports


def normalize(definition):
    def stage1():
        attributes_needed = ["headers", "dlls", "url", "signatures"]
        attributes_missing = []
        for attribute in attributes_needed:
            if attribute not in definition or definition[attribute] is None:
                attributes_missing.append(attribute)
        if attributes_missing:
            raise AttributeError(
                f"Definition {definition.get('name')} missing attributes for function definition: {', '.join(attributes_missing)}")

    def stage2():
        sig_attributes_needed = ["name", "ret", "params", "inline", "noexcept", "vararg"]
        for signature in definition.get("signatures", []):
            sig_attributes_missing = []
            for attribute in sig_attributes_needed:
                if attribute not in signature or signature[attribute] is None:
                    sig_attributes_missing.append(attribute)
            if sig_attributes_missing:
                raise AttributeError(
                    f"Definition {definition.get('name')} missing attributes for function definition: {', '.join(sig_attributes_missing)}")

    stage1()
    stage2()
    for i, v in enumerate(definition["headers"]):
        definition["headers"][i] = v.lower()
    for i, v in enumerate(definition["dlls"]):
        definition["dlls"][i] = v.lower()


def generate_loader_from_definition(definition, opts):
    generated_signature_code = []

    def generate_signature_code(signature, header, dll):
        signature_param_parts = []
        for param in signature["params"]:
            signature_param_parts.append(f"{param['type']} {param['name']}")
        definition_param_string = ", ".join(signature_param_parts)

        noexcept_string = "noexcept" if signature["noexcept"] else ""

        function_header_without_semi = f"{signature['ret']} {signature['name']} ({definition_param_string}) {noexcept_string}"
        global_memo_variable = f"$$GLOB$${signature['name']}"

        signature_args_parts = []
        for param in signature["params"]:
            signature_args_parts.append(param['name'])
        signature_args_string = ", ".join(signature_args_parts)

        function_body = f"""{{
    if (!{global_memo_variable}) {{
        {global_memo_variable} = (decltype({signature['name']})*) load_function((char*)"{dll}", (char*)"{signature['name']}");
    }}
    return {global_memo_variable}({signature_args_string});
}}"""

        function_implementation = f"""{function_header_without_semi}
    {function_body}"""

        function_header = f"""inline decltype({signature['name']})* {global_memo_variable};"""

        function_include = f"""#include "{header}\""""

        return {
            "include": function_include,
            "header": function_header,
            # if the function has already been declared inline in the header, it must have been manually defined.
            "implementation": "" if signature["inline"] else function_implementation,
        }

    for signature in definition["signatures"]:
        for dll in definition["dlls"]:
            if opts["exclude_dlls"].count(dll.lower()) > 0:
                continue
            generated_signature_code.append(generate_signature_code(signature, definition["headers"][0], dll))
            break

    return generated_signature_code


def should_generate_signature_code(definition, opts):
    if opts.get("executable_imports"):
        for executable_import in opts["executable_imports"]:
            for signature in definition["signatures"]:
                potential_import_name = signature["name"]
                if potential_import_name == executable_import["name"]:
                    opts["executable_imports"].remove(executable_import)
                    return True
        return False
    else:
        return True


def generate_loaders(database, opts):
    structure = {}

    for definition in database:
        try:
            normalize(definition)
            should_generate = should_generate_signature_code(definition, opts)
            if not should_generate:
                continue
            processed_list = generate_loader_from_definition(definition, opts)
            header = definition.get("headers")[0]
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

            for processed in processed_list:
                includes.add(processed['include'])
                headers.append(processed['header'])
                implementations.append(processed['implementation'])

        except AttributeError as e:
            print(e, file=sys.stderr)

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

        includes_list = list(function_data['includes'])

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
    parser.add_argument("-i", "--input", dest="input", required=True, help="Input database")
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
    executable_imports = []
    exclude_dlls = []

    if args.executable:
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
        shutil.copytree("winloader", args.output_implementation, False, ignore=shutil.ignore_patterns(""),
                        dirs_exist_ok=True)

    includes_string = "\n".join(includes)
    includes_string_wrapped = f"""#pragma once
    
{includes_string}
"""
    with open(args.output_summary, "w") as f:
        f.write(includes_string_wrapped)
