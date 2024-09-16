import json
import os

from generator import preparation, builder
from helpers.import_generator import generate_import_libraries
from helpers.signature import processor

if __name__ == '__main__':
    os.makedirs("temp", exist_ok=True)
    with open("test_implicit.json", "r") as f:
        data = json.load(f)
    generate_import_libraries(data, "temp")