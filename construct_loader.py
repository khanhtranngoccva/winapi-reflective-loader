from clang import cindex
import generator.types
import helpers.cindex.modifications


def construct_loader(signature, match: generator.types.FunctionMatch):
    node = match.node

    # Already defined functions should not have loaders that conflict with the default loader.
    if node.is_definition():
        return None

    # Functions without a DLL cannot have a loader.
    if not signature.get("dlls"):
        return None

    arguments = list(node.get_arguments())

    is_inlined = node.is_function_inlined()
    is_variadic = node.type.is_function_variadic()

    variadic_list_variable = "$$VAR$$variadic_arguments"
    output_variable = "$$VAR$$output"
    global_memo_variable = f"$$GLOB$${node.spelling}"

    param_tokens = []
    delegated_arg_tokens = []
    for i, arg in enumerate(arguments):
        spelling = arg.spelling
        while delegated_arg_tokens.count(spelling) > 0:
            spelling = "_" + spelling
        param_tokens.append(f"{arg.type.spelling} {arg.spelling}")
        delegated_arg_tokens.append(arg.spelling)

    if is_variadic:
        param_tokens.append("...")
        delegated_arg_tokens.append(variadic_list_variable)
        variadic_list_part1 = f"""va_list {variadic_list_variable};
    va_start({variadic_list_variable}, {delegated_arg_tokens[-2]});"""
        variadic_list_part2 = f"""va_end({variadic_list_variable});"""
    else:
        variadic_list_part1 = ""
        variadic_list_part2 = ""

    param_str = ", ".join(param_tokens)
    delegated_arg_str = ", ".join(delegated_arg_tokens)

    inline_str = "inline" if is_inlined else ""

    header_declaration_without_semicolon = f"{inline_str} {node.result_type.spelling} {node.spelling} ({param_str})".strip()

    if node.result_type.spelling != "void":
        out_assignment = f"""{node.result_type.spelling} {output_variable} = """
        return_statement = f"""return {output_variable};"""
    else:
        out_assignment = ""
        return_statement = ""

    function_body = f"""{{
    if (!{global_memo_variable}) {{
        {global_memo_variable} = (decltype({node.spelling})*) load_function((char*)"{signature["dlls"][0]}", (char*)"{node.mangled_name}");
    }}
    {variadic_list_part1}
    {out_assignment}{global_memo_variable}({delegated_arg_str});
    {variadic_list_part2}
    {return_statement}
}}"""

    implementation = f"""{header_declaration_without_semicolon} {function_body}"""
    global_variable = f"inline decltype({node.spelling})* {global_memo_variable};"

    extra_includes = []
    if is_variadic:
        extra_includes.append("stdarg.h")

    return generator.types.Loader(node.spelling, node.mangled_name, implementation, global_variable, extra_includes)
