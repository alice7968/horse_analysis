import os
import pandas as pd
from bs4 import BeautifulSoup
from step06_get_horse_parents import retry_failed_html_fetch

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)
HTML_DIR = PARENTDIR + "/race_horse_id_htmls"
CSV_OUTPUT_PATH = PARENTDIR + "/horse_pedigree_extracted.csv"

def merge_parents_data():
    # 既存データの読み込み（キャッシュ）
    if os.path.exists(CSV_OUTPUT_PATH):
        existing_df = pd.read_csv(CSV_OUTPUT_PATH, dtype=str)
        existing_ids = set(existing_df["horse_id"])
    else:
        existing_df = pd.DataFrame()
        existing_ids = set()

    records = []
    # ファイルごとに処理
    for filename in os.listdir(HTML_DIR):
        if not filename.endswith(".html"):
            continue

        horse_id = filename.replace(".html", "")
        if horse_id in existing_ids:
            continue

        file_path = os.path.join(HTML_DIR, filename)

        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

            table = soup.find("table", class_="blood_table")
            if not table:
                continue

            summary = table.get("summary", "")
            horse_name = summary.replace("の血統表", "") if "の血統表" in summary else ""

            tds = table.find_all("td")
            anchors = [td.find("a") for td in tds if td.find("a")]
            anchor_info = [(a.get("title", a.text), a["href"].split("/")[-2]) for a in anchors]

            record = {
                "horse_id": horse_id,
                "horse_name": horse_name
            }

            keys = [
                "parent_ml", "parent_ml_ml", "parent_ml_fml",
                "parent_fml", "parent_fml_ml", "parent_fml_fml"
            ]

            for key, (name, pid) in zip(keys, anchor_info):
                record[f"{key}_name"] = name
                record[f"{key}_id"] = pid

            records.append(record)

    # DataFrameへ変換・保存
    df = pd.DataFrame(records)
    final_df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset=["horse_id"])
    final_df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"✅ 血統データを保存しました: {CSV_OUTPUT_PATH}")

    # horse_nameが空のhorse_idを抽出して保存
    empty_name_df = final_df[final_df["horse_name"] == ""]
    EMPTY_NAME_OUTPUT_PATH = PARENTDIR + "/horse_ids_with_empty_name.csv"
    if os.path.exists(EMPTY_NAME_OUTPUT_PATH):
        existing_ids = pd.read_csv(EMPTY_NAME_OUTPUT_PATH)["horse_id"].dropna().astype(str).tolist()
    else:
        existing_ids = []

    new_ids = empty_name_df["horse_id"].dropna().astype(str).tolist()
    combined_ids = sorted(set(existing_ids + new_ids))

    pd.DataFrame(combined_ids, columns=["horse_id"]).to_csv(EMPTY_NAME_OUTPUT_PATH, index=False, encoding="utf-8")
    print(f"⚠️ horse_nameが空のhorse_id {len(empty_name_df)} 個を抽出して保存しました: {EMPTY_NAME_OUTPUT_PATH}")

    # 再試行ループ
    while True:
        # 空のhorse_nameを持つhorse_idを再取得
        if not os.path.exists(EMPTY_NAME_OUTPUT_PATH):
            break

        empty_ids_df = pd.read_csv(EMPTY_NAME_OUTPUT_PATH)
        input_ids = empty_ids_df["horse_id"].dropna().astype(str).tolist()

        if not input_ids:
            break

        print(f"🔁 {len(input_ids)} 件の再取得を実行中...")
        retry_failed_html_fetch(HTML_DIR, input_ids)

        # 再度マージと抽出を実行
        records = []
        for filename in os.listdir(HTML_DIR):
            if not filename.endswith(".html"):
                continue

            horse_id = filename.replace(".html", "")
            if horse_id in existing_ids:
                continue

            file_path = os.path.join(HTML_DIR, filename)

            with open(file_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "html.parser")

                table = soup.find("table", class_="blood_table")
                if not table:
                    continue

                summary = table.get("summary", "")
                horse_name = summary.replace("の血統表", "") if "の血統表" in summary else ""

                tds = table.find_all("td")
                anchors = [td.find("a") for td in tds if td.find("a")]
                anchor_info = [(a.get("title", a.text), a["href"].split("/")[-2]) for a in anchors]

                record = {
                    "horse_id": horse_id,
                    "horse_name": horse_name
                }

                keys = [
                    "parent_ml", "parent_ml_ml", "parent_ml_fml",
                    "parent_fml", "parent_fml_ml", "parent_fml_fml"
                ]

                for key, (name, pid) in zip(keys, anchor_info):
                    record[f"{key}_name"] = name
                    record[f"{key}_id"] = pid

                records.append(record)

        df = pd.DataFrame(records)
        final_df = pd.concat([existing_df, df], ignore_index=True).drop_duplicates(subset=["horse_id"])
        final_df.to_csv(CSV_OUTPUT_PATH, index=False, encoding="utf-8")
        print(f"✅ 再抽出後の血統データを保存しました: {CSV_OUTPUT_PATH}")

        empty_name_df = final_df[final_df["horse_name"] == ""]
        if os.path.exists(EMPTY_NAME_OUTPUT_PATH):
            existing_ids = pd.read_csv(EMPTY_NAME_OUTPUT_PATH)["horse_id"].dropna().astype(str).tolist()
        else:
            existing_ids = []

        new_ids = empty_name_df["horse_id"].dropna().astype(str).tolist()
        combined_ids = sorted(set(existing_ids + new_ids))

        pd.DataFrame(combined_ids, columns=["horse_id"]).to_csv(EMPTY_NAME_OUTPUT_PATH, index=False, encoding="utf-8")
        print(f"⚠️ horse_nameが空のhorse_id {len(empty_name_df)} 個を抽出して保存しました: {EMPTY_NAME_OUTPUT_PATH}")

        if len(empty_name_df) == 0:
            print("🎉 全てのhorse_nameを正常に取得できました！")
            break

if __name__ == "__main__":
    merge_parents_data()