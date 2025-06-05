import pandas as pd
import glob
import re
from dateutil import parser
import numpy as np
import os

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)
OWN = PARENTDIR + "/csv/"

def horse_data_cleaner():
    
    # CSV読み込み
    horse_files = glob.glob(OWN + "horse-*.csv")
    df_horse = pd.concat([pd.read_csv(f) for f in horse_files], ignore_index=True)
    # race_id + horse_id で重複行を削除
    df_horse = df_horse.drop_duplicates(subset=["race_id", "horse_id"], keep="first")
    race_file = glob.glob(OWN + "race-*.csv")
    df_race = pd.concat([pd.read_csv(f) for f in race_file], ignore_index=True)

    df_horse["race_id"] = df_horse["race_id"].astype(str).str.strip()
    df_race["race_id"] = df_race["race_id"].astype(str).str.strip()
    # race_dataの"date"を取り込み、df_horseにrace_idでマージ
    df_horse = pd.merge(df_horse, df_race[["race_id", "date"]], on="race_id")
    # 年月日をゼロ埋めしながら整形し、漢字を除去して8桁の数値に変換
    df_horse["date"] = df_horse["date"].astype(str)
    date_parts = df_horse["date"].str.extract(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
    date_parts.dropna(inplace=True)
    df_horse.loc[date_parts.index, "date"] = date_parts.apply(lambda x: f"{int(x[0]):04}{int(x[1]):02}{int(x[2]):02}", axis=1)
    df_horse["date"] = pd.to_numeric(df_horse["date"], errors="coerce").astype("Int64")

    # race_dataの"date"を文字列に変換せずそのままマージ
    # 形式はdatetimeのまま保持

    # sex_and_age分解
    def extract_sex_flags(val):
        if pd.isna(val):
            return pd.Series([0, 0, 0])
        is_senba = 1 if "セ" in val else 0
        is_mesu = 1 if "牝" in val else 0
        is_osu = 1 if "牡" in val else 0
        return pd.Series([is_senba, is_mesu, is_osu])

    def extract_age(val):
        return int("".join(filter(str.isdigit, str(val)))) if pd.notna(val) else None

    sex_flags = df_horse["sex_and_age"].apply(extract_sex_flags)
    sex_flags.columns = ["is_senba", "is_mesu", "is_osu"]
    df_horse = pd.concat([df_horse, sex_flags], axis=1)
    df_horse["age"] = df_horse["sex_and_age"].apply(extract_age)

    # 通過順位から最初の数値を抽出しrankとの差分計算
    def extract_first_rank(s):
        if pd.isna(s): return None
        parts = str(s).split("-")
        for part in parts:
            if part.isdigit():
                return int(part)
        return None

    df_horse["half_way_first"] = df_horse["half_way_rank"].apply(extract_first_rank)
    df_horse["rank_dif"] = pd.to_numeric(df_horse["rank"], errors='coerce')
    df_horse["half_way_dif"] = df_horse["half_way_first"] - df_horse["rank_dif"]

    # goal_timeを秒換算
    def convert_goal_time_to_seconds(time_str):
        if pd.isna(time_str) or not isinstance(time_str, str):
            return None
        parts = time_str.split(":")
        try:
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return round(minutes * 60 + seconds, 2)
            else:
                return float(parts[0])
        except:
            return None

    df_horse["goal_time"] = df_horse["goal_time"].apply(convert_goal_time_to_seconds)

    # race_idによる結合でdistance取得
    df_merged = pd.merge(df_horse, df_race[["race_id", "race_course"]], on="race_id", how="left")
    # distance の抽出処理を強化
    df_merged["distance"] = (
        df_merged["race_course"].astype(str).str.extract(r'(\d+)')[0].astype("Int64")
    )

    # コースの向きを抽出し数値化（右=1、左=2、直線=0）
    def extract_course_direction(text):
        if isinstance(text, str):
            for direction in ["右", "左", "直線"]:
                if direction in text:
                    return direction
        return None

    df_merged["direction"] = df_merged["race_course"].apply(extract_course_direction).map({"左": 2, "右": 1, "直線": 0})
    # ave_velocity の算出（型安全に）
    df_merged["ave_velocity"] = (
        df_merged["distance"].astype(float) / df_merged["goal_time"].astype(float)
    )

    #一応完全重複削除
    df_merged = df_merged.drop_duplicates()
    # 不要列削除
    df_merged.drop(columns=["goal_time_dif", "half_way_rank", "half_way_first", "rank_dif", "race_course"], errors='ignore', inplace=True)

    # horse_weightの整形
    df_merged["horse_weight"] = df_merged["horse_weight"].astype(str).str.replace(r"\(.*", "", regex=True)

    # horse_weightをfloatに変換し、horse_idごとにdate昇順で前走との差分を計算
    df_merged["horse_weight"] = pd.to_numeric(df_merged["horse_weight"], errors="coerce")
    # 同じ horse_id, race_id で複数行ある場合、一つ前のdateを参照し horse_weight_dif を再計算
    df_merged = df_merged.sort_values(["horse_id", "date"])
    df_merged["prev_weight"] = df_merged.groupby("horse_id")["horse_weight"].shift(1)
    df_merged["horse_weight_dif"] = df_merged["horse_weight"] - df_merged["prev_weight"]
    df_merged.drop(columns=["prev_weight"], inplace=True)
    df_merged = df_merged.drop_duplicates(subset=["race_id", "horse_id"], keep="first")

    # 型変換
    df_merged = df_merged[df_merged["rank"] != "中"]
    # rank列が1〜18の整数以外の値を持つ行を削除
    df_merged = df_merged[pd.to_numeric(df_merged["rank"], errors="coerce").between(1, 18)]
    # 指定カラムをすべて整数型（Int64）に変換
    int_cols = ["frame_number", "horse_number", "horse_id", "rider_id", "popular",
                "tamer_id", "owner_id", "date", "age", "half_way_dif", "distance", "direction"]
    for col in int_cols:
        if col in df_merged.columns:
            df_merged[col] = pd.to_numeric(df_merged[col], errors="coerce")
            if df_merged[col].isna().any():
                df_merged[col] = df_merged[col].fillna(-1)  # または dropna() でもよい
            df_merged[col] = df_merged[col].astype("Int64")


    # 完全重複行削除
    df_cleaned = df_merged.drop_duplicates()

    # 保存
    df_cleaned.to_csv("final_cleaned_horse_data.csv", index=False)


if __name__ == "__main__":
    horse_data_cleaner()
    print("整形完了: final_cleaned_horse_data.csv")