import os
import shutil
import subprocess


def generate_import_libraries(data, output_directory):
    shutil.rmtree(output_directory, ignore_errors=True)
    os.makedirs(output_directory, exist_ok=True)
    for group in data:
        dll = group['dll']
        functions = group['functions']
        export_string = "\n".join(" " * 4 + func for func in functions)
        output_def = f"""LIBRARY {dll}
EXPORTS 
{export_string}"""
        dll_no_ext, _ = os.path.splitext(dll)
        output_def_path = os.path.join(output_directory, f"loader-{dll_no_ext}.def")
        output_def_lib = os.path.join(output_directory, f"loader-{dll_no_ext}.lib")

        with open(output_def_path, "w") as f:
            f.write(output_def)

        proc = subprocess.Popen([
            "lib.exe",
            f"/DEF:{output_def_path}",
            f"/OUT:{output_def_lib}",
        ])

        proc.communicate()
        if proc.returncode != 0:
            print(f"Library generation for {dll} exited with code {proc.returncode}")
