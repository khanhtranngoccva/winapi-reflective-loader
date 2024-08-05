from clang import cindex
import helpers.cindex.modifications

index = cindex.Index.create()
parsed = index.parse("./test.hpp", options=cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD)
for inc in parsed.get_includes():
    inc: cindex.FileInclusion
    # print(inc.source)
cur = parsed.cursor

for node in cur.walk_preorder():
    node: cindex.Cursor
    if node.kind.name == "FUNCTION_DECL" or node.kind.name == "MACRO_DEFINITION":
        # print(node.kind, node.spelling)

        # print(node.spelling)
        if node.spelling == "RtlUnwindEx":
            for arg in node.get_arguments():
                print(arg.type.spelling, arg.spelling)
            break
        # print(node.is_definition())
        # ret_type: cindex.Type = node.result_type
        # print(node.mangled_name)
        # print(ret_type.get_canonical())
        # for child in node.get_children():
        #     print(child.kind, child.spelling)
