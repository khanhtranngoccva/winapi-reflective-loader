import hashlib
import json
import os
import re

import constants
from helpers.errors import EntrySaveError, EntryCacheCheckError


def hash_entry(entry):
    return hashlib.md5(entry["url"].encode("utf-8")).hexdigest()


def generate_save_path(entry):
    save_fn = f"{hash_entry(entry)}.json"
    save_path = os.path.join(constants.ROOT_PATH, "database", save_fn)
    return save_path


def should_process_entry(entry, program_args):
    save_path = generate_save_path(entry)
    if program_args.headers:
        return program_args.headers.count(entry.get("header", "").lower()) > 0
    if program_args.specific_functions:
        # In case function has ANSI and Unicode variants
        tests = [
            entry["name"],
            entry["name"] + "A",
            entry["name"] + "W",
        ]
        for test in tests:
            if program_args.specific_functions.count(test) > 0:
                return True
        return False
    if program_args.static_only and not entry.get("static"):
        return False
    try:
        with open(save_path, "r") as file:
            try:
                json.load(file)
            except json.decoder.JSONDecodeError:
                return True
    except FileNotFoundError:
        return True
    except Exception as e:
        raise EntryCacheCheckError(entry, e)
    else:
        if not program_args.cached:
            return True
    return False


def save_entry(result):
    save_path = generate_save_path(result)
    try:
        with open(save_path, "w") as f:
            f.write(json.dumps(result, indent=2))
    except Exception as e:
        raise EntrySaveError(result, e)


def deduplicate_entries(entries):
    url_set = set()
    deduplicated_function_entries = []

    def try_add_entry(entry):
        if entry["url"] in url_set:
            return
        url_set.add(entry["url"])
        deduplicated_function_entries.append(entry)

    # Let static entries have more precedence over dynamic entries by attempting to add them first.
    for entry in entries:
        if entry.get("static"):
            try_add_entry(entry)
    for entry in entries:
        try_add_entry(entry)
    return deduplicated_function_entries


if __name__ == '__main__':
    initial = "ReadConsoleA"
    print(re.sub("A|W$", "", initial))
