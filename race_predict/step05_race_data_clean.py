import re
import pandas as pd
import glob
import os
import unicodedata
import re
import os

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)
OWN = PARENTDIR + "/csv"

def race_data_cleaner(input_folder: str, output_file: str):
    # race-*.csv ファイルを全て取得
    csv_files = glob.glob(os.path.join(input_folder, OWN + "/race-*.csv"))
    all_dfs = []

    for file in csv_files:
        try:
            df = pd.read_csv(file)
            #df["source_file"] = os.path.basename(file)  # 任意: 元ファイル名の記録
            all_dfs.append(df)
        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")

    if not all_dfs:
        print("❌ No race data files loaded.")
        return

    # データ結合
    combined_df = pd.concat(all_dfs, ignore_index=True)

    # race_id の最初の1つだけ残す（重複を削除）
    cleaned_df = combined_df.drop_duplicates(subset="race_id", keep="first")

    cleaned_df["race_round"] = cleaned_df["race_round"].astype(str).str.replace(r"\s*R", "", regex=True)
    cleaned_df.rename(columns={"race_round": "race_number"}, inplace=True)
    cleaned_df["weather"] = cleaned_df["weather"].astype(str).str.replace("天候 : ", "")

    def split_ground_status(val):
        if pd.isna(val):
            return pd.NA, pd.NA, 0
        if ":" in val or "：" in val:
            parts = re.split(r"\s*[：:]\s*", val)
            return parts[0], parts[1] if len(parts) > 1 else pd.NA, 0
        return pd.NA, val, 0

    split_results = cleaned_df["ground_status"].apply(split_ground_status)
    cleaned_df["surface"] = split_results.apply(lambda x: x[0])
    cleaned_df["ground_status"] = split_results.apply(lambda x: x[1])
    # ground_status から "芝" または "ダート" を削除し、元に含まれていた行の is_obstacle を 1 にする
    contains_surface = cleaned_df["ground_status"].astype(str).str.contains("芝|ダート", na=False)
    cleaned_df["ground_status"] = cleaned_df["ground_status"].astype(str).str.replace("芝", "", regex=False)
    cleaned_df["ground_status"] = cleaned_df["ground_status"].astype(str).str.replace("ダート", "", regex=False)
    cleaned_df["ground_status"] = cleaned_df["ground_status"].astype(str).str.replace("  ", "", regex=False)
    cleaned_df["is_obstacle"] = split_results.apply(lambda x: x[2])
    # 該当行の is_obstacle を 1 にする (augment, not overwrite)
    cleaned_df.loc[contains_surface, "is_obstacle"] = 1

    racecourse_dict = {
        "01": "札幌", "02": "函館", "03": "福島", "04": "新潟", "05": "東京",
        "06": "中山", "07": "中京", "08": "京都", "09": "阪神", "10": "小倉"
    }
    reverse_racecourse_dict = {v: k for k, v in racecourse_dict.items()}
    
    cleaned_df.drop(columns=["date"], inplace=True)
    cleaned_df["where_racecourse"] = cleaned_df["where_racecourse"].str.extract(r"\d+回(.*?)\d+日目")
    if "race_course" in cleaned_df.columns:
        cleaned_df.drop(columns=["race_course"], inplace=True)
    cleaned_df.rename(columns={"where_racecourse": "race_course"}, inplace=True)
    cleaned_df.rename(columns={"total_horse_number": "headcount"}, inplace=True)
    cleaned_df["headcount"] = cleaned_df["headcount"].astype("Int64")
    cleaned_df["frame_number_first"] = cleaned_df["frame_number_first"].astype("Int64")
    cleaned_df["horse_number_first"] = cleaned_df["horse_number_first"].astype("Int64")
    cleaned_df["frame_number_second"] = cleaned_df["frame_number_second"].astype("Int64")
    cleaned_df["horse_number_second"] = cleaned_df["horse_number_second"].astype("Int64")
    cleaned_df["frame_number_third"] = cleaned_df["frame_number_third"].astype("Int64")
    cleaned_df["horse_number_third"] = cleaned_df["horse_number_third"].astype("Int64")
    cleaned_df["race_course_id"] = cleaned_df["race_course"].map(reverse_racecourse_dict)

    columns_order = [
        "race_id","race_number","weather","surface","ground_status","race_course","headcount",
        "frame_number_first","horse_number_first","frame_number_second","horse_number_second",
        "frame_number_third","horse_number_third","tansyo","hukusyo_first","hukusyo_second","hukusyo_third",
        "wakuren","umaren","wide_1_2","wide_1_3","wide_2_3","umatan","renhuku3","rentan3",
        "is_obstacle","race_course_id"
    ]

    # 存在しないカラムはNaNで埋める
    for col in columns_order:
        if col not in cleaned_df.columns:
            cleaned_df[col] = pd.NA

    # カラムの順番を指定通りに並べ替え
    cleaned_df = cleaned_df[columns_order]

    '''
    def remove_mojibake(text):
        import re
        if not isinstance(text, str):
            text = str(text)
        try:
            text = text.encode('utf-8', 'ignore').decode('utf-8', 'ignore')
        except Exception:
            pass
        return re.sub(r'[^\x00-\x7Fぁ-んァ-ヶー一-龯。、！？「」（）・]+', '', text)

    for col in cleaned_df.columns:
        cleaned_df[col] = cleaned_df[col].astype(str).apply(remove_mojibake)
        '''
    
    # 保存
    cleaned_df.fillna(-1)
    cleaned_df.to_csv(output_file, index=False)

if __name__ == "__main__":
    input_folder = PARENTDIR  # race-*.csvが置かれているディレクトリ
    output_file = "final_cleaned_race_data.csv"
    race_data_cleaner(input_folder, output_file)