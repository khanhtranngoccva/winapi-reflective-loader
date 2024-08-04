import json
import os
import sys

for root, dirs, files in os.walk("database"):
    for file in files:
        path = os.path.join(root, file)
        try:
            with open(path, "r") as file_handle:
                data = json.load(file_handle)
            dlls = []
            for dll in data["dlls"]:
                if dll:
                    dlls.append(dll)
            data["dlls"] = dlls
            with open(path, "w") as file_handle:
                json.dump(data, file_handle, indent=2)
        except json.decoder.JSONDecodeError:
            print(f"Path {path} parse failed.", file=sys.stderr)
