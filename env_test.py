from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

driver = webdriver.Chrome(
    service=Service(ChromeDriverManager(
        url="https://registry.npmmirror.com/-/binary/chromedriver/"
    ).install())
)
