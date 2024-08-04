import os
import re

from pathvalidate import is_valid_filename
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from WebPage import WebPage
from helpers.errors import EntryProcessingError, WebError, RequirementParsingError


def get_function_data(function_entry):
    if not function_entry.get("url") or not function_entry.get("name"):
        raise RuntimeError(f"Failure to get function data - invalid parameters. {function_entry}")

    with WebPage(function_entry.get("url")) as web_page:
        driver = web_page.get_driver()
        content_node = driver.find_element(By.CSS_SELECTOR, "#main .content")
        syntax_node = content_node.find_element(By.CSS_SELECTOR, "div:has(#syntax)")
        content_node_children = driver.find_elements(By.CSS_SELECTOR, "#main .content > *")
        syntax_node_index = content_node_children.index(syntax_node)
        code: str | None = None
        for i in range(syntax_node_index, len(content_node_children)):
            if content_node_children[i].tag_name == "pre":
                code = content_node_children[i].find_element(By.CSS_SELECTOR, "code").text
                break
        if not code:
            raise EntryProcessingError(function_entry)

        requirement_node = content_node.find_element(By.CSS_SELECTOR, "div:has(#requirements)")
        requirement_node_index = content_node_children.index(requirement_node)

        requirement_table_body = None
        for i in range(requirement_node_index, len(content_node_children)):
            try:
                cur_node = content_node_children[i]
                requirement_table_body = cur_node.find_element(By.CSS_SELECTOR, "table")
            except NoSuchElementException:
                pass
        if not requirement_table_body:
            raise WebError(f"Failure to get function data for {function_entry} - requirement table not found.")

        requirement_data = {}
        for row in requirement_table_body.find_elements(By.CSS_SELECTOR, "tbody tr"):
            cells = row.find_elements(By.CSS_SELECTOR, "td")
            requirement_data[cells[0].text.strip().lower()] = cells[1].text.strip()

    name = function_entry["name"]

    try:
        headers = extract_filenames(requirement_data["header"], [".h", ".hpp", ".cuh"]) if requirement_data.get(
            "header") else []
        dlls = extract_filenames(requirement_data["dll"], [".dll"]) if requirement_data.get(
            "dll") else []
    except Exception as e:
        raise RequirementParsingError(function_entry, requirement_data)

    function_data = {"names": name, "code": code, "headers": headers, "dlls": dlls, "url": function_entry["url"]}
    return function_data


def extract_filenames(raw, extensions):
    tokens = re.split(r"[^\w.\-_]", raw)
    result: set[str] = set()
    for token in tokens:
        if is_valid_filename(token):
            token_ext = os.path.splitext(token)[1].lower()
            for ext in extensions:
                if token_ext.lower() == ext:
                    result.add(token.lower())
    return list(result)