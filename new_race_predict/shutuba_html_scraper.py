from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)

def save_race_pages_from_urls(date_str):
    ALT_RACE_URL_DIR = PARENTDIR + "/alt_race_url"
    year = date_str[:4]
    month = str(int(date_str[4:6]))
    day = str(int(date_str[6:8]))
    SAVE_DIR = os.path.join(PARENTDIR,"alt_race_html", year, month, day)
    os.makedirs(SAVE_DIR, exist_ok=True)

    url_file = os.path.join(ALT_RACE_URL_DIR, f"{date_str}.txt")
    if not os.path.exists(url_file):
        print(f"URLファイルが見つかりません: {url_file}")
        return

    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f.readlines() if line.strip()]

    options = Options()
    #options.page_load_strategy = 'eager'
    options.add_argument('--headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=options)

    for i, url in enumerate(urls):
        race_id = url.split("race_id=")[-1].split("&")[0]
        save_path = os.path.join(SAVE_DIR, f"{race_id}.html")
        if os.path.exists(save_path):
            print(f"既に保存済み: {save_path} をスキップします。")
            continue
        try:
            print(url)
            driver.get(url)
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "RaceData01")))
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME, "RaceData02")))
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "thead")))
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.TAG_NAME, "tbody")))
            thead_html = driver.find_element(By.TAG_NAME, "thead").get_attribute("outerHTML")
            tbody_html = driver.find_element(By.TAG_NAME, "tbody").get_attribute("outerHTML")
            race_data01_html = driver.find_element(By.CLASS_NAME, "RaceData01").get_attribute("outerHTML")
            race_data02_html = driver.find_element(By.CLASS_NAME, "RaceData02").get_attribute("outerHTML")
            html = race_data01_html + race_data02_html + thead_html + tbody_html
            save_path = os.path.join(SAVE_DIR, f"{race_id}.html")
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            print(f"{url} の保存に失敗しました: {e}")

    driver.quit()

if __name__ == "__main__":
    date_str = input("日付を8桁（YYYYMMDD）で入力してください: ")
    save_race_pages_from_urls(date_str)