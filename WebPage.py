import urllib3
from bs4 import BeautifulSoup
import urllib.parse
from selenium import webdriver

from selenium.webdriver.chrome.options import Options

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument('--log-level=3')
chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
chrome_options.set_capability("browserVersion", "117")


class WebPage:
    def __init__(self, url):
        try:
            self.__opened = True
            self.__url = url
            self.__driver = webdriver.Chrome(options=chrome_options)
            self.__driver.get(url)
            self.__content = self.__driver.page_source
        except Exception as e:
            self.close()
            raise e

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_driver(self):
        return self.__driver

    def get_full_anchor_url(self, url):
        return urllib.parse.urljoin(self.__url, url)

    def get_url(self):
        return self.__url

    def close(self):
        try:
            self.__driver.quit()
        except:
            pass
