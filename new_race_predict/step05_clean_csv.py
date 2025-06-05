import os
import pandas as pd


 # CSV 読み込み（ファイル名は必要に応じて変更）
input_base = input("日付は？(例：20230401): ")
input_path = input_base + ".csv"
output_path = input_base + "_with_frame_type.csv"
parent_dir = os.path.dirname(os.getcwd())
input_dir = os.path.join("alt_race_csv", input_base[:4], str(int(input_base[4:6])))
df = pd.read_csv(os.path.join(os.getcwd(), input_dir, input_path))

# ここで merge_df を読み込む（パスは環境に応じて変更）
merge_df_path = os.path.join(os.getcwd(), "merge_df.csv")
merge_df = pd.read_csv(merge_df_path)

# 標準化された馬番を計算
df["standard_horse_number"] = df["horse_number"] / df["headcount"]

# 初期値を 0 で埋める
df["frame_type"] = 0

# 条件に応じて分類
df.loc[
    (df["standard_horse_number"] >= 0.0) & (df["standard_horse_number"] < 0.25),
    "frame_type"
] = 1  # 内枠

df.loc[
    (df["standard_horse_number"] >= 0.25) & (df["standard_horse_number"] < 0.5),
    "frame_type"
] = 2  # 中内枠

df.loc[
    (df["standard_horse_number"] >= 0.5) & (df["standard_horse_number"] < 0.75),
    "frame_type"
] = 3  # 中外枠

df.loc[
    (df["standard_horse_number"] >= 0.75) & (df["standard_horse_number"] <= 1.0),
    "frame_type"
] = 4  # 外枠

# 必要な特徴量のリスト（一部は後で無視）
feature_cols = ['race_id', 'date','race_course_id','race_number','surface','distance','direction',
                'headcount','frame_number','horse_number','horse_weight','age',
                'is_senba','is_mesu','is_osu','horse_id','rider_id','tamer_id',
                'weather','ground_status','is_obstacle','frame_type',
                'analy_horse_type',
                'parent_ml_id','parent_ml_ml_id','parent_ml_fml_id',
                'parent_fml_id','parent_fml_ml_id','parent_fml_fml_id']

# 存在しないカラムを 0 で作成する処理
for col in feature_cols:
    if col not in df.columns:
        df[col] = 0

# 不要なカラムを削除
df = df[[col for col in feature_cols if col in df.columns]]

 # 型の調整（int型にできるものはintにする。ただしカテゴリ値はマッピング）
weather_map = {'晴': 1, '曇': 2, '小雨': 3, '雨': 4, '小雪': 5, '雪': 6}

int_columns = ['race_course_id','race_number','surface','distance','direction','headcount',
               'frame_number','horse_number','age','is_senba','is_mesu','is_osu','horse_id',
               'rider_id','tamer_id','weather','ground_status','is_obstacle','frame_type']
for col in int_columns:
    if col in ['weather', 'ground_status']:
        if col == 'weather':
            df[col] = df[col].map(weather_map).fillna(-1).astype(int)
        
    else:
        if df[col].isnull().any():
            df[col] = df[col].fillna(-1)
        df[col] = df[col].astype(int)


#
# df と merge_df を縦に結合して、analy_horse_type を過去データから分析する
df["source"] = "target"
merge_df["source"] = "past"
combined_df = pd.concat([merge_df, df], ignore_index=True)


# グループ化用のデータは過去データだけに限定
past_data = combined_df[combined_df["source"] == "past"].copy()
past_data = past_data[past_data["horse_type"] > 0]
past_data = past_data.sort_values(["horse_id", "date"])
grouped = past_data.groupby("horse_id")

# analy_horse_type を割り当て
analy_horse_types = []
for idx, row in df.iterrows():
    horse_id = row["horse_id"]
    race_date = row["date"]
    if horse_id not in grouped.groups:
        analy_horse_types.append(0)
        continue
    past = grouped.get_group(horse_id)
    past = past[past["date"] < race_date]["horse_type"]
    if past.empty:
        analy_horse_types.append(0)
    else:
        analy_horse_types.append(past.mode().iloc[0])

# 結果を設定
df["analy_horse_type"] = analy_horse_types
df["analy_horse_type"] = df["analy_horse_type"].astype(int)

# 不要になったsource列を削除
df.drop(columns=["source"], inplace=True)
merge_df.drop(columns=["source"], inplace=True)

# --- 血統情報の追加処理 ---
pedigree_path = os.path.join(os.getcwd(), "horse_pedigree_extracted.csv")
pedigree_df = pd.read_csv(pedigree_path)
# 型をそろえる
pedigree_df["horse_id"] = pedigree_df["horse_id"].astype(str).str.strip().astype(int)
df["horse_id"] = df["horse_id"].astype(str).str.strip().astype(int)

# 必要な血統カラムを明示的に指定
pedigree_cols = [
    "parent_ml_id", "parent_ml_ml_id", "parent_ml_fml_id",
    "parent_fml_id", "parent_fml_ml_id", "parent_fml_fml_id"
]

# カラムが存在することを確認
missing_cols = [col for col in pedigree_cols if col not in pedigree_df.columns]
if missing_cols:
    raise ValueError(f"Missing expected pedigree columns: {missing_cols}")

# 必要なカラムだけ抽出
pedigree_df = pedigree_df[["horse_id"] + pedigree_cols]

# 結合処理
df = df.merge(pedigree_df, on="horse_id", how="left", suffixes=('', '_ped'))

# 欠損値は 0 で埋める
df[pedigree_cols] = df[pedigree_cols].fillna(0).astype(int)

# ---- Drop original columns and rename _ped columns ----
cols_to_drop = [
    "parent_ml_id", "parent_ml_ml_id", "parent_ml_fml_id",
    "parent_fml_id", "parent_fml_ml_id", "parent_fml_fml_id"
]
cols_rename = {
    "parent_ml_id_ped": "parent_ml_id",
    "parent_ml_ml_id_ped": "parent_ml_ml_id",
    "parent_ml_fml_id_ped": "parent_ml_fml_id",
    "parent_fml_id_ped": "parent_fml_id",
    "parent_fml_ml_id_ped": "parent_fml_ml_id",
    "parent_fml_fml_id_ped": "parent_fml_fml_id"
}
# Drop original columns if they exist
df = df.drop(columns=[col for col in cols_to_drop if col in df.columns])
# Rename _ped columns if they exist
df = df.rename(columns={k: v for k, v in cols_rename.items() if k in df.columns})


# 血統IDが全て欠損 or 0 の horse_id を抽出して保存
empty_pedigree = df[
    (df[pedigree_cols].fillna(0) == 0).all(axis=1)
]
empty_pedigree_ids = empty_pedigree["horse_id"].unique()
empty_output_path = os.path.join(os.getcwd(), "horse_ids_with_empty_name.csv")
pd.Series(empty_pedigree_ids, name="horse_id").to_csv(empty_output_path, index=False)
print(f"Saved unmatched horse IDs to {empty_output_path}")

# 結果を保存
df.to_csv(os.path.join(os.getcwd(), output_path), index=False)
print(f"Saved processed data to {output_path}")