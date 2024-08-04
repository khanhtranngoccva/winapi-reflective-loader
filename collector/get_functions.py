import pprint
import re
import traceback

from selenium.webdriver.common.by import By

from WebPage import WebPage


def get_function_from_side_entry(data: str):
    tokens = data.split(" ")
    if len(tokens) < 1:
        return None
    entry_type = " ".join(tokens[1:])
    if entry_type == "function":
        return tokens[0]


def get_functions_by_technology_entry(category_entry):
    with WebPage(category_entry["url"]) as web_page:
        driver = web_page.get_driver()

        functions = []

        left_container_list_items = driver.find_elements(By.CSS_SELECTOR,
                                                         "#affixed-left-container ul.table-of-contents > li")
        for left_container_list_item in left_container_list_items:
            text = left_container_list_item.text
            if not re.match(r"\S+\.h(pp)?", text, re.IGNORECASE):
                continue
            function_header = text.lower()
            left_container_list_item.click()
            sub_items = left_container_list_item.find_elements(By.CSS_SELECTOR, "ul > li")
            for item in sub_items:
                function_name = get_function_from_side_entry(item.text)
                if function_name is not None:
                    functions.append({
                        "name": function_name,
                        "url": web_page.get_full_anchor_url(
                            item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")),
                        "header": function_header
                    })
        return functions


def get_functions_by_header_entry(category_entry):
    with WebPage(category_entry["url"]) as web_page:
        driver = web_page.get_driver()

        functions = []

        left_container_list_items = driver.find_elements(By.CSS_SELECTOR,
                                                         "#affixed-left-container ul.table-of-contents > li")
        for item in left_container_list_items:
            function_name = get_function_from_side_entry(item.text)
            if function_name is not None:
                functions.append({
                    "name": function_name,
                    "url": web_page.get_full_anchor_url(
                        item.find_element(By.CSS_SELECTOR, "a").get_attribute("href")),
                    "header": category_entry["header"].lower()
                })
        return functions


if __name__ == '__main__':
    pprint.pp(get_functions_by_technology_entry({
        "url": "https://learn.microsoft.com/en-us/windows/win32/api/fileapi/",
        "header": "Fileapi.h"
    }))
