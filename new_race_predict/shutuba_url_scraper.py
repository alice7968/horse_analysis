from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from urllib.parse import urlparse, parse_qs
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_race_urls_for_date(date_str, headless=True):
    base_url = "https://race.netkeiba.com/top/"

    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(base_url)

    wait = WebDriverWait(driver, 15)
    # <li>要素から aria-controls を取得し、その中の <a> をクリック
    try:
        parent_li = wait.until(EC.presence_of_element_located(
            (By.XPATH, f'//li[a[contains(@href, "kaisai_date={date_str}")]]')
        ))
        aria_controls = parent_li.get_attribute("aria-controls")
        if not aria_controls:
            print(f"{date_str} のリンクには aria-controls 属性がありません。")
            driver.quit()
            return []
    except Exception as e:
        print(f"aria-controls の取得に失敗しました: {e}")
        driver.quit()
        return []

    #print("aria-controls:", aria_controls)

    date_link = parent_li.find_element(By.TAG_NAME, "a")
    driver.execute_script("arguments[0].click();", date_link)
    
    wait.until(EC.presence_of_element_located((By.ID, aria_controls)))
    parent_section = driver.find_element(By.ID, aria_controls)

    time.sleep(3)  # 遷移後の読み込み待機

    try:
        elements = parent_section.find_elements(By.CSS_SELECTOR, 'a[href*="shutuba.html"], a[href*="result.html"]')
        race_urls = []
        for link in elements:
            href = link.get_attribute('href')
            if "top_pickup" in href:
                continue
            if "result.html" in href:
                href = href.replace("result.html", "shutuba.html")
            race_urls.append(href)
    except Exception as e:
        print(f"Error occurred: {e}")
        race_urls = []
    finally:
        driver.quit()

    # Save to alt_race_url directory
    import os
    OWNDIR = os.path.dirname(os.path.abspath(__file__))
    PARENTDIR = os.path.dirname(OWNDIR)
    ALT_RACE_URL_DIR = PARENTDIR + "/alt_race_url"
    if not os.path.exists(ALT_RACE_URL_DIR):
        os.makedirs(ALT_RACE_URL_DIR)
    output_file = os.path.join(ALT_RACE_URL_DIR, f"{date_str}.txt")
    with open(output_file, 'w') as f:
        for url in race_urls:
            f.write(url + '\n')

    return race_urls


if __name__ == "__main__":
    date_str = input("日付を8桁（YYYYMMDD）で入力してください: ")
    get_race_urls_for_date(date_str)