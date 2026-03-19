
def get_error():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    import time
    import tempfile

    from bs4 import BeautifulSoup

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")
    driver = webdriver.Chrome(options=options)
    try:
        driver.get("http://10.14.0.98:35010/prepare")
        time.sleep(5)  # 等页面 JS 加载完成
        html = driver.page_source
    except Exception as e:
        print(f"访问日志页面时发生错误: {e}")
        html = None

    driver.close()  # 关闭当前标签页
    driver.quit()

    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    try:
        logs = soup.find_all("div", {"data-testid": "LogLine"})
        error_logs = [
            div.get_text() for div in logs
            if div.find("span", {"data-testid": "replaceLogLevel"})
            and "ERROR" in div.get_text()
        ]
        text = "\n".join(error_logs)
        # log_div = soup.find("div", {"data-testid": "LogLine"})
        # level = log_div.find("span", class_="token").text
        # text = log_div.get_text(separator="\n", strip=True)
        # print(f"Level: {level}")
        # print(f"Text: {text}")
    except Exception as e:
        print(f"解析日志时发生错误: {e}")
        text = ""


    return text

if __name__ == "__main__":
    get_error()