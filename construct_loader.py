import hashlib

from clang import cindex
import generator.types
import helpers.cindex.modifications


def generate_struct_members(buf_length):
    data_member_sizes = [
        (8, "unsigned __int64"),
        (4, "unsigned __int32"),
        (2, "unsigned __int16"),
        (1, "unsigned __int8"),
    ]
    while buf_length > 0:
        for candidate_size, data_type in data_member_sizes:
            if buf_length >= candidate_size:
                buf_length -= candidate_size
                yield candidate_size, data_type
                break


def transform_string_to_struct(variable_name, encoded_string: bytes, null_byte=True):
    if null_byte:
        encoded_string += b"\0"  # Null byte
    encoded_length = len(encoded_string)
    member_index = 0
    current_seek = 0
    struct_name = f"$$STRINGTYPE$${variable_name}"
    struct_var = f"{variable_name}"
    members = []
    instructions = []
    for member_size, data_type in generate_struct_members(encoded_length):
        member_name = f"m{member_index}"
        member_value = int.from_bytes(encoded_string[current_seek:current_seek + member_size], byteorder="little")
        member_instruction = f"{struct_var}.{member_name} = {member_value}U;"
        instructions.append(member_instruction)
        member_declaration = f"{data_type} {member_name};"
        members.append(member_declaration)
        current_seek += member_size
        member_index += 1

    member_string = "\n".join(members)
    instruction_string = "\n".join(instructions)
    output = f"""typedef struct {struct_name} {{
{member_string}
}} {struct_name};
    
{struct_name} {struct_var};
{instruction_string}  
"""
    return output


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

    name_hash = hashlib.sha256()
    name_hash.update(node.mangled_name.encode("ansi"))
    name_hash_digest = name_hash.digest()
    name_hash_var = "$$VAR$$func_hash"
    name_hash_instructions = transform_string_to_struct(name_hash_var, name_hash_digest, null_byte=True)

    function_body = f"""{{
{name_hash_instructions}
if (!{global_memo_variable}) {{
    {global_memo_variable} = (decltype({node.spelling})*) winloader::load_function_by_hash((char*)"{signature["dlls"][0]}", (char*)&{name_hash_var});
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
