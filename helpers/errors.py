import collections.abc
import copy
import datetime
import json
import os
import sys
import traceback
import uuid

import constants


def serialize(obj, *_, serialize_stack=None):
    try:
        if not serialize_stack:
            serialize_stack = {*""}
        if obj is None:
            return obj
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        if isinstance(obj, int):
            return obj
        if isinstance(obj, float):
            return obj
        if isinstance(obj, str):
            return obj
        if isinstance(obj, bool):
            return obj
        if id(obj) in serialize_stack:
            return "<<CIRCULAR_REFERENCE>>"
        recursive_stack = copy.copy(serialize_stack)
        recursive_stack.add(id(obj))
        out_obj = {
            "__dict": {}
        }
        if hasattr(obj, "__dict__"):
            for k, v in obj.__dict__.items():
                out_obj["__dict"][k] = serialize(v, serialize_stack=recursive_stack)
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                out[k] = serialize(v, serialize_stack=recursive_stack)
            out_obj["__type"] = "__PURE_DICT__"
            out_obj["__value"] = out
            return out_obj
        if isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, set) or isinstance(obj,
                                                                                                 collections.abc.Iterable):
            out = []
            for v in obj:
                out.append(serialize(v, serialize_stack=recursive_stack))
            out_obj["__type"] = "__PURE_ITERABLE__"
            out_obj["__value"] = out
            return out_obj
        if callable(obj):
            out_obj["__type"] = "__PURE_CALLABLE__"
            out_obj["__name"] = obj.__name__
            return out_obj
        else:
            out_obj["__type"] = type(obj).__name__
            if hasattr(obj, "__repr__"):
                out_obj["__repr__"] = obj.__repr__()
            if hasattr(obj, "__str__"):
                out_obj["__str__"] = obj.__str__()
            if isinstance(obj, Exception):
                out_obj["__traceback"] = traceback.format_exception(obj)
            return out_obj
    except Exception as e:
        print(e, file=sys.stderr)
        print(obj, file=sys.stderr)


execution_time = datetime.datetime.now().isoformat().replace(":", "_")
error_dir = os.path.join(constants.ROOT_PATH, "errors", execution_time)
os.makedirs(error_dir, exist_ok=True)


def save_to_disk(error):
    current_time = datetime.datetime.now().isoformat().replace(":", "_")
    save_dir = os.path.join(error_dir, type(error).__name__)
    os.makedirs(save_dir, exist_ok=True)
    save_location = os.path.join(save_dir, f"{current_time}.json")
    with open(save_location, "w") as f:
        save_data = serialize(error)
        json.dump(save_data, f, indent=2)


class EntryProcessingError(RuntimeError):
    def __init__(self, function_entry):
        super().__init__()
        self.name = function_entry.get("name")
        self.url = function_entry.get("url")
        self.header = function_entry.get("header")

    def __repr__(self):
        return "Failure to process entry: {}".format(self.name)


class SignatureProcessingError(EntryProcessingError):
    def __init__(self, entry, signature):
        super().__init__(entry)
        self.signature = signature

    def __repr__(self):
        return "Failure to process entry due to hint and signature mismatch: {}".format(self.name)


class RequirementParsingError(EntryProcessingError):
    def __init__(self, entry, requirement_data):
        super().__init__(entry)
        self.requirement_data = requirement_data

    def __repr__(self):
        return "Failure to process entry due to hint and signature mismatch: {}".format(self.name)


class WebError(EntryProcessingError):
    def __repr__(self):
        return "Failure to process entry due to web/element issues: {}".format(self.name)


class ParseError(RuntimeError):
    def __init__(self, signature):
        self.signature = signature

    def __repr__(self):
        return "Failure to process signature: {}".format(self.signature)


class EntrySaveError(RuntimeError):
    def __init__(self, entry, nested_error):
        super().__init__()
        self.entry = entry
        self.nested_error = nested_error

    def __repr__(self):
        return "Failure to save entry: {}".format(self.entry.get("name"))


class DefineSearchError(RuntimeError):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def __repr__(self):
        return "Failed to search for defines in entry: {}".format(self.path)


class AliasCollectionError(RuntimeError):
    def __init__(self, path, e):
        super().__init__()
        self.path = path
        self.nested_error = e

    def __repr__(self):
        return "Failed to search for aliases in header {}: {}".format(self.path, self.nested_error)


class EntryCacheCheckError(RuntimeError):
    def __init__(self, entry, nested_error):
        super().__init__()
        self.entry = entry
        self.nested_error = nested_error

    def __repr__(self):
        return "Failure to save entry: {}".format(self.entry.get("name"))
