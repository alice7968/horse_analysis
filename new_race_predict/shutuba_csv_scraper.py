from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import chardet
import os

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)

def make_shutuba_csv(date_str):
    racecourse_dict = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
        "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
    }
    month_folder = str(int(date_str[4:6]))
    day_folder = str(int(date_str[6:8]))
    target_folder = f"{PARENTDIR}/alt_race_html/{date_str[:4]}/{month_folder}/{day_folder}"
    if not os.path.exists(target_folder):
        print(f"指定されたフォルダが見つかりません: {target_folder}")
        return
    html_files = [os.path.join(target_folder, f) for f in os.listdir(target_folder) if f.endswith(".html")]

    all_dataframes = []
    for html_path in html_files:
        with open(html_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            encoding = result['encoding']

        # BeautifulSoupでHTMLを読み込み
        soup = BeautifulSoup(raw_data.decode(encoding, errors='ignore'), 'html.parser')

        # theadからカラム名を抽出（最初の11個、3番目の"印"を除外）
        thead = soup.find("thead")
        if thead is None:
            print(f"⚠ thead not found in file: {html_path}, skipping.")
            continue
        th_tags = thead.find_all("th")
        column_names = []
        for th in th_tags[:11]:
            aria_label = th.get("aria-label", "")
            parts = aria_label.split(":")[0].split()
            col_name = parts[0].strip() if parts else "Unknown"
            if col_name == "オッズ":
                col_name = "odds"
            column_names.append(col_name)
        if len(column_names) >= 3 and column_names[2] == "印":
            del column_names[2]
        column_names = column_names[:10]

        # tbodyのtrをデータとして取得
        tbody = soup.find("tbody", attrs={"aria-live": "polite"})
        rows = []
        if tbody is None:
            print(f"⚠ tbody not found in file: {html_path}, skipping.")
            continue
        for tr in tbody.find_all("tr"):
            tds = tr.find_all("td")
            row = [td.get_text(strip=True) if td.get_text(strip=True) else np.nan for td in tds]
            rows.append(row)

        # データフレームに変換
        race_table_data = pd.DataFrame(rows)

        # 不要な列（3列目, 12〜15列目）を削除
        cols_to_drop = [2, 11, 12, 13, 14]
        race_table_data.drop(columns=[col for col in cols_to_drop if col < race_table_data.shape[1]], inplace=True)

        # カラム名を修正
        column_names = [col if "馬体重" not in col else "horse_weight" for col in column_names]
        column_names = ["frame_number" if col == "枠" else col for col in column_names]
        column_names = ["horse_number" if col == "馬番" else col for col in column_names]
        column_names = ["popular" if col == "人気" else col for col in column_names]
        column_names = ["burden_weight" if col == "斤量" else col for col in column_names]

        # カラム名を設定
        race_table_data.columns = column_names
        # 馬体重カラムのクレンジング
        if "horse_weight" in race_table_data.columns:
            race_table_data["horse_weight"] = race_table_data["horse_weight"].astype(str)
            race_table_data["horse_weight"] = race_table_data["horse_weight"].str.replace(r"\(.*", "", regex=True)

        # 性齢カラムを分離
        if "性齢" not in race_table_data.columns:
            print(f"⚠ '性齢' column not found in file: {html_path}, skipping.")
            continue
        race_table_data["性別"] = race_table_data["性齢"].str.extract(r'([牡牝セ])')
        race_table_data["年齢"] = race_table_data["性齢"].str.extract(r'(\d+)')
        race_table_data.rename(columns={"年齢": "age"}, inplace=True)
        # 性別ダミー変数の作成
        race_table_data["is_senba"] = (race_table_data["性別"] == "セ").astype(int)
        race_table_data["is_mesu"] = (race_table_data["性別"] == "牝").astype(int)
        race_table_data["is_osu"] = (race_table_data["性別"] == "牡").astype(int)
        race_table_data.drop(columns=["性別"], inplace=True)

        # 馬名・騎手・厩舎のリンクからIDを抽出
        def extract_id(td):
            a = td.find('a')
            if a and 'href' in a.attrs:
                return a['href'].split("/")[-1]
            return np.nan

        def extract_id_2(td):
            a = td.find('a')
            if a and 'href' in a.attrs:
                return a['href'].split("/")[-2]
            return np.nan

        # 馬名(td index=3), 騎手(7), 厩舎(9)のtdからIDを取得
        horse_ids = []
        rider_ids = []
        tamer_ids = []

        trs = tbody.find_all("tr")
        for tr in trs:
            tds = tr.find_all("td")
            horse_id = extract_id(tds[3]) if len(tds) > 3 else np.nan
            rider_id = extract_id_2(tds[6]) if len(tds) > 6 else np.nan
            tamer_id = extract_id_2(tds[7]) if len(tds) > 7 else np.nan
            horse_ids.append(horse_id)
            rider_ids.append(rider_id)
            tamer_ids.append(tamer_id)

        # カラムに追加
        race_table_data["horse_id"] = horse_ids
        race_table_data["rider_id"] = rider_ids
        race_table_data["tamer_id"] = tamer_ids

        # レースIDをファイル名から抽出してrace_idカラムとして追加
        race_id = os.path.splitext(os.path.basename(html_path))[0]
        place_code = race_id[4:6]
        race_course_name = racecourse_dict.get(place_code, "不明")
        race_table_data.insert(0, "race_id", race_id)
        race_table_data.insert(1, "race_course", race_course_name)
        reverse_racecourse_dict = {v: k for k, v in racecourse_dict.items()}
        race_table_data["race_course_id"] = race_table_data["race_course"].map(reverse_racecourse_dict)
        race_number = str(int(race_id[-2:]))
        race_table_data.insert(2, "race_number", race_number)

        # レース名などの追加情報を抽出
        race_name_tag = soup.find("h1", class_="RaceName")
        race_name = race_name_tag.get_text(strip=True).split("\n")[0] if race_name_tag else np.nan

        data01_div = soup.find("div", class_="RaceData01")
        data01 = data01_div.get_text(strip=True) if data01_div else ""
        import re
        weather_match = re.search(r"天候[:：](\S+)", data01)
        ground_match = re.search(r"馬場[:：](\S+)", data01)
        weather = weather_match.group(1) if weather_match else np.nan
        ground = ground_match.group(1) if ground_match else np.nan
        time_match = re.search(r"(\d{1,2}:\d{2})発走", data01)
        surface_match = re.search(r"(芝|ダ)", data01)
        distance_match = re.search(r"(\d{3,4})m", data01)
        direction_match = re.search(r"\(([^)]+)\)", data01)

        data02_div = soup.find("div", class_="RaceData02")
        data02 = data02_div.get_text(strip=True) if data02_div else ""
        headcount_match = re.search(r"(\d+)頭", data02)

        start_time = time_match.group(1) if time_match else np.nan
        surface = surface_match.group(1) if surface_match else np.nan
        distance = distance_match.group(1) if distance_match else np.nan
        direction_raw = direction_match.group(1).replace('\xa0', ' ') if direction_match else np.nan
        direction_raw_str = str(direction_raw) if not isinstance(direction_raw, str) else direction_raw
        direction = re.search(r"(左|右|直線)", direction_raw_str).group(1) if re.search(r"(左|右|直線)", direction_raw_str) else np.nan
        headcount = headcount_match.group(1) if headcount_match else np.nan

        # race_nameを左から2列目、その他は最後に追加
        race_table_data.insert(1, "race_name", race_name)
        race_table_data["start_time"] = start_time
        race_table_data["surface"] = surface
        race_table_data["surface"] = race_table_data["surface"].map({"ダ": 0, "芝": 1})
        race_table_data["distance"] = distance
        race_table_data["direction"] = direction
        race_table_data["direction"] = race_table_data["direction"].map({"左": 2, "右": 1, "直線": 0})
        race_table_data["headcount"] = headcount
        race_table_data["weather"] = weather
        race_table_data["weather"] = race_table_data["weather"].astype(str).str.replace("/", "", regex=False)
        race_table_data["ground_status"] = ground
        race_table_data["ground_status"] = race_table_data["ground_status"].map({"良": 1, "稍": 2, "重": 3, "不": 4})

        race_table_data["date"] = date_str
        race_table_data["is_obstacle"] = race_table_data["race_name"].apply(lambda x: 0 if pd.isna(x) else (1 if "障害" in x else 0))

        # Reorder columns as requeste
        desired_order = [
            "race_id",
            "date",              # 2nd
            "start_time",        # 3rd
            "race_course",       # 4th
            "race_number",       # 5th
            "race_name",         # 6th
            "surface",           # 7th
            "distance",          # 8th
            "direction",         # 9th
            "headcount"          # 10th
        ]
        remaining_columns = [col for col in race_table_data.columns if col not in desired_order]
        race_table_data = race_table_data[desired_order + remaining_columns]

        all_dataframes.append(race_table_data)

    final_df = pd.concat(all_dataframes, ignore_index=True)
    month = str(int(date_str[4:6]))
    output_dir = f"{PARENTDIR}/alt_race_csv/{date_str[:4]}/{month}"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "{date_str}.csv".format(date_str=date_str))
    final_df.to_csv(output_path, index=False, encoding="utf-8-sig")

if __name__ == "__main__":
    date_str = input("日付を8桁（YYYYMMDD）で入力してください: ")
    make_shutuba_csv(date_str)