import pandas as pd
import os
import requests 
import time
from py2slack import send_slack
from bs4 import BeautifulSoup

urls = []

def get_horse_parents_urls():
    OWNDIR = os.path.dirname(os.path.abspath(__file__))
    OWN = os.path.dirname(OWNDIR)

    df = pd.read_csv(os.path.join(OWN, "final_cleaned_horse_data.csv"))
    df = df[~df["rank"].astype(str).str.contains(r"(除|中|取)", na=False)]
    df.dropna(how="any", inplace=True)
    unique_ids = df["horse_id"].dropna().unique()
    
    for horse_id in unique_ids:
        try:
            int_id = int(float(horse_id))
            urls.append(f"https://db.netkeiba.com/horse/{int_id}/")
        except:
            continue

    output_dir = os.path.join(OWN, "race_horse_id_urls")
    output_path = os.path.join(output_dir, "horse_urls.txt")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    with open(output_path, "w", encoding="utf-8") as f:
        for url in urls:
            f.write(url + "\n")

def get_race_horse_htmls():
    OWNDIR = os.path.dirname(os.path.abspath(__file__))
    OWN = os.path.dirname(OWNDIR)
    headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    } #ユーザーエージェント偽装
    input_path = os.path.join(OWN, "race_horse_id_urls", "horse_urls.txt")
    output_dir = os.path.join(OWN, "race_horse_id_htmls")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(input_path, "r", encoding="utf-8") as f:
        htmls = [line.strip() for line in f if line.strip()]
    
    total = len(htmls)
    processed = 0
    last_percent = -1
    
    already_exists_count = 0
    for html in htmls:
        horse_id = html.rstrip("/").split("/")[-1]
        save_file = os.path.join(output_dir, f"{horse_id}.html")
        if os.path.isfile(save_file):
            already_exists_count += 1
            continue
    print(f"{already_exists_count} HTML files already exist and were skipped.")
    print(f"{len(urls) - already_exists_count} HTML files will be fetched.")

    for i, html in enumerate(htmls):
        try:
            horse_id = html.rstrip("/").split("/")[-1]
            save_file = os.path.join(output_dir, f"{horse_id}.html")
            if os.path.isfile(save_file):
                continue

            response = requests.get(html, headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(1)

            with open(save_file, "w", encoding="utf-8") as file:
                soup = BeautifulSoup(response.text, "html.parser")
                blood_table = soup.find("table", class_="blood_table")
                if blood_table:
                    file.write(str(blood_table))
                else:
                    print(f"No blood table found for {html}")

            processed += 1
            percent = int(((processed + already_exists_count) / total) * 100)
            if percent > last_percent:
                print(f"Progress: {percent}%")
                last_percent = percent

        except Exception as e:
            print(f"Failed to fetch {html}: {e}")
            send_slack("400 Client Error")
            break

def retry_failed_html_fetch(output_dir, input_ids):
    OWNDIR = os.path.dirname(os.path.abspath(__file__))
    OWN = os.path.dirname(OWNDIR)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36'
    }
    last_percent = -1
    total = len(input_ids)

    for i, horse_id in enumerate(input_ids):
        save_file = os.path.join(output_dir, f"{horse_id}.html")
        url = f"https://db.netkeiba.com/horse/{horse_id}/"
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            time.sleep(1)
            # BeautifulSoup側で自動エンコーディング判断
            soup = BeautifulSoup(response.content, "html.parser")
            blood_table = soup.find("table", class_="blood_table")
            if blood_table:
                with open(save_file, "w", encoding="utf-8") as file:
                    file.write(str(blood_table))
                input_ids = [hid for hid in input_ids if hid != horse_id]
                pd.DataFrame(input_ids, columns=["horse_id"]).to_csv(os.path.join(OWN, "horse_ids_with_empty_name.csv"), index=False)
            else:
                print(f"No blood table found for {url}")
        except Exception as e:
            print(f"Retry failed for {url}: {e}")
            
        percent = int((i / total) * 100)
        if percent > last_percent:
            print(f"Progress: {percent}%")
            last_percent = percent
    
if __name__ == "__main__":
    get_horse_parents_urls()
    get_race_horse_htmls()
    send_slack("parents_dataの取得の準備が整いました")
    
    '''
    failed_ids_path = os.path.join(OWN, "horse_ids_with_empty_name.csv")
    output_dir = os.path.join(OWN, "race_horse_id_htmls")
    input_ids = pd.read_csv(failed_ids_path)["horse_id"].dropna().astype(str).tolist()
    #retry_failed_html_fetch(output_dir, input_ids)
    '''
