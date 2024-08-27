import hashlib
import random
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
        candidates = []
        for candidate_size, data_type in data_member_sizes:
            if buf_length >= candidate_size:
                candidates.append([candidate_size, data_type])
        if candidates:
            candidate_size, data_type = random.choice(candidates)
            buf_length -= candidate_size
            yield candidate_size, data_type


def generate_member_instruction(struct_var, member_name, data_type, byte_slice, byte_order):
    head = f"{struct_var}.{member_name} = "
    slice_length = len(byte_slice)
    xor_val = int.from_bytes(random.randbytes(slice_length), byteorder="little")
    original_member_value = int.from_bytes(byte_slice, byteorder="little")
    obfuscated_le_value = xor_val ^ original_member_value
    if byte_order == "little":
        expr = f"winloader::n_xor<{data_type}>({obfuscated_le_value}U, {xor_val}U)"
    else:
        obfuscated_be_value = int.from_bytes(obfuscated_le_value.to_bytes(slice_length, byteorder="little"),
                                             byteorder="big")
        # original_member_value = endian_swap(obfuscated_be_value) ^ xor_val
        expr = f"winloader::n_xor<{data_type}>(winloader::endian_swap(({data_type}) {obfuscated_be_value}U), {xor_val}U)"
    return f"{head} {expr};"


def transform_buffer_to_struct(variable_name, encoded_string: bytes, null_bytes=1):
    for i in range(null_bytes):
        encoded_string += b"\0"  # Null byte
    encoded_length = len(encoded_string)
    member_index = 0
    current_seek = 0
    struct_name = f"$$STRINGTYPE$${variable_name}"
    struct_var = f"{variable_name}"
    members = []
    instructions = []
    for member_size, data_type in generate_struct_members(encoded_length):
        byte_order = "little"
        if member_size > 1 and random.randrange(0, 3):
            # 2/3 chance for member to be big-endian and 1/3 chance to be little-endian
            byte_order = "big"
        member_name = f"m{member_index}"
        byte_slice = encoded_string[current_seek:current_seek + member_size]
        member_instruction = generate_member_instruction(struct_var, member_name, data_type, byte_slice, byte_order)
        instructions.append(member_instruction)
        member_declaration = f"{data_type} {member_name};"
        members.append(member_declaration)
        current_seek += member_size
        member_index += 1

    # This helps confuse some smarter detection engines - they can detect multiple mov instructions and conclude that
    # there is a hidden string in the form of a struct.
    random.shuffle(instructions)

    member_string = "\n".join(members)
    instruction_string = "\n".join(instructions)
    output = f"""#pragma pack(push, 1)
typedef struct {struct_name} {{
{member_string}
}} {struct_name};
#pragma pack(pop)

{struct_name} {struct_var};
{instruction_string}  
"""
    return output


def transform_string_to_stack_string(var_name, string_item, encoding):
    if encoding == "utf-16le":
        char_size = 2
        data_type = "wchar_t"
    elif encoding == 'utf-8':
        char_size = 1
        data_type = "char"
    elif encoding == 'ansi':
        char_size = 1
        data_type = "char"
    else:
        raise Exception("Other encodings are not supported.")
    impl_var_name = f"$$STACKSTRING$${var_name}"
    member_instructions = transform_buffer_to_struct(impl_var_name, string_item.encode(encoding), char_size)
    cast_instruction = f"auto {var_name} = ({data_type}*) &{impl_var_name};"
    return f"""{member_instructions}
{cast_instruction}"""


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
    name_hash_instructions = transform_buffer_to_struct(name_hash_var, name_hash_digest, null_bytes=1)

    dll_name_var = "$$VAR$$dll_name"
    dll_instructions = transform_string_to_stack_string(dll_name_var, signature["dlls"][0], encoding="utf-8")

    function_body = f"""{{
if (!{global_memo_variable}) {{
    {name_hash_instructions}
    {dll_instructions}
    {global_memo_variable} = (decltype({node.spelling})*) winloader::load_function_by_hash({dll_name_var}, (char*)&{name_hash_var});
}}
{variadic_list_part1}
{out_assignment}{global_memo_variable}({delegated_arg_str});
{variadic_list_part2}
{return_statement}
}}"""

    implementation = f"""#pragma optimize("", off)
    {header_declaration_without_semicolon} {function_body}
#pragma optimize("", on)"""

    # implementation = f"""{header_declaration_without_semicolon} {function_body}"""

    global_variable = f"inline decltype({node.spelling})* {global_memo_variable};"

    extra_includes = []
    if is_variadic:
        extra_includes.append("stdarg.h")

    return generator.types.Loader(node.spelling, node.mangled_name, implementation, global_variable, extra_includes)


if __name__ == '__main__':
    print(transform_string_to_stack_string("cim_namespace", "root\\cimv2".encode("utf-16le"), 2))
