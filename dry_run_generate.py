import json

from generator import preparation, builder
from helpers.signature import processor

if __name__ == '__main__':
    with open("./test_definition.json", "r") as f:
        definition = json.load(f)
        preparation.normalize(definition)
        sigs = preparation.get_signatures(definition)
        for signature in sigs:
            parsed = processor.parse_builtin_header("winuser.h", cached=False)
            cursor = parsed.cursor
            for entry in cursor.walk_preorder():
                if entry.kind.name != "FUNCTION_DECL" or entry.spelling != "GetCursorPos":
                    continue
                print(entry.displayname)
