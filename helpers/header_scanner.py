import fnmatch
import os


def scan_header_files_recursive(paths: list[str]):
    for path in paths:
        for parent_dir, dirs, files in os.walk(path):
            for file in files:
                if fnmatch.fnmatch(file, "*.h") or fnmatch.fnmatch(file, "*.hpp") or fnmatch.fnmatch(file, "*.cuh"):
                    yield parent_dir, file
