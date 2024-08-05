import pprint
import urllib.parse
from urllib.parse import urlparse
from selenium.webdriver.common.by import By
from helpers.WebPage import WebPage


def get_category_urls():
    with WebPage("https://learn.microsoft.com/en-us/windows/win32/api/") as web_page:
        driver = web_page.get_driver()

        api_homepage_path = urlparse(web_page.get_url()).path

        urls_technologies = list()
        urls_headers = list()

        # Find in main page.
        content_areas = driver.find_elements(By.CSS_SELECTOR, "#landing-content .box")
        for content_area in content_areas:
            current_heading_node = None
            for node in content_area.get_property("children"):
                if node.tag_name == "h3":
                    current_heading_node = node.text.strip().lower()
                if current_heading_node != "reference":
                    continue
                if node.tag_name != "ul":
                    continue
                for link in node.find_elements(By.CSS_SELECTOR, "li a"):
                    href = link.get_property("href")
                    if not urllib.parse.urlparse(href).path.startswith(api_homepage_path):
                        continue
                    urls_technologies.append({
                        "url": web_page.get_full_anchor_url(href),
                    })

        toc_area_nodes = driver.find_elements(By.CSS_SELECTOR, "#affixed-left-container ul > li")
        for toc_area_node in toc_area_nodes:
            # Find in "technologies" column in the table of contents area.
            if toc_area_node.text.lower() == "technologies":
                toc_area_node.click()
                links = toc_area_node.find_elements(By.CSS_SELECTOR, "li a")
                for link in links:
                    href = link.get_property("href")
                    if not urllib.parse.urlparse(href).path.startswith(api_homepage_path):
                        continue
                    urls_technologies.append({
                        "url": web_page.get_full_anchor_url(href)
                    })
            elif toc_area_node.text.lower() == "headers":
                toc_area_node.click()
                links = toc_area_node.find_elements(By.CSS_SELECTOR, "li a")
                for link in links:
                    href = link.get_property("href")
                    if not urllib.parse.urlparse(href).path.startswith(api_homepage_path):
                        continue
                    urls_headers.append({
                        "header": link.text,
                        "url": web_page.get_full_anchor_url(href),
                    })

    return {
        "technologies": urls_technologies,
        "headers": urls_headers,
        "total_entries": len(urls_technologies) + len(urls_headers),
    }


if __name__ == '__main__':
    result = get_category_urls()
    pprint.pprint(result)
    pprint.pprint(len(result))
