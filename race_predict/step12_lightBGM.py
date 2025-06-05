import pandas as pd
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import os

OWNDIR = os.path.dirname(os.path.abspath(__file__))
PARENTDIR = os.path.dirname(OWNDIR)

# ファイルの読み込み
merged_data = pd.read_csv(PARENTDIR + "/merge_df.csv", low_memory=False)

# ガーベル（非デコード可能な）テキストを含む行を削除
import chardet

def is_garbled(row):
    for val in row.astype(str):
        try:
            val.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError:
            return True
    return False

merged_data = merged_data[~merged_data.apply(is_garbled, axis=1)]

# rank を数値に変換（済み）
merged_data['rank'] = pd.to_numeric(merged_data['rank'], errors='coerce')

# target: 3着以内なら1、その他は0（明示的に定義し直す）
merged_data['target'] = merged_data['rank'].apply(lambda x: 1 if x <= 3 else 0)

# float形式になっている日付を文字列にしてから日付型に変換
merged_data['date'] = pd.to_datetime(
    merged_data['date'].dropna().astype(int).astype(str), format='%Y%m%d', errors='coerce')


# データ分割
train_data = merged_data[(merged_data['date'] >= '2020-01-01') & (merged_data['date'] <= '2023-12-31')]
test_data = merged_data[merged_data['date'] >= '2024-01-01']

print("test_data 件数:", len(test_data))

# 明示的に特徴量カラムを指定
feature_cols = ['date',
                'race_course_id','race_number','surface','distance','direction',
                'headcount','frame_number','horse_number',
                #'horse_weight',
                #'odds','popular',
                'age',
                'is_senba','is_mesu','is_osu',
                'horse_id',
                'rider_id',
                'tamer_id',
                'weather','ground_status','is_obstacle',
                'frame_type',
                'analy_horse_type',
                'parent_ml_id','parent_ml_ml_id','parent_ml_fml_id','parent_fml_fml_id'
                ]

# ラベルエンコーディング
X_train = train_data[feature_cols].copy()
X_test = test_data[feature_cols].copy()


# 数値に変換できる列はすべて数値型に変換（エラーがあればNaNに）
for col in X_train.columns:
    X_train[col] = pd.to_numeric(X_train[col], errors='coerce')
    X_test[col] = pd.to_numeric(X_test[col], errors='coerce')


for col in X_train.select_dtypes(include='object').columns:
    le = LabelEncoder()
    X_train[col] = le.fit_transform(X_train[col].astype(str))
    X_test[col] = le.transform(X_test[col].astype(str))

X_train = X_train.fillna(0)
X_test = X_test.fillna(0)
y_train = train_data['target']
y_test = test_data['target']

# LightGBMで学習・予測
model = lgb.LGBMClassifier()

model.fit(X_train, y_train)

# 特徴量重要度の取得
importance = model.feature_importances_
feature_names = X_train.columns
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': importance
}).sort_values(by='importance', ascending=False)

# 表示
print("\n重要な特徴量 上位10件:")
print(importance_df.head(10))


probs = model.predict_proba(X_test)[:, 1]
preds = (probs >= 0.6).astype(int)

# 結果出力

print("ROC AUC:", roc_auc_score(y_test, probs))
print(classification_report(y_test, preds))

# test_data に予測結果を追加
test_data = test_data.copy()
test_data['pred'] = preds
test_data['prob'] = probs
#test_data['odds'] = pd.to_numeric(test_data['odds'], errors='coerce')


# 複勝購入対象（予測が1＝3着以内と予想
bets = test_data[(test_data['pred'] == 1) & (test_data['is_obstacle'] == 0)]
hits = bets[bets['target'] == 1]

# 払戻金取得（first/second/third から該当馬のものを取得）
# horse_number（馬番）を基に、どの複勝払い戻し列が該当するか確認する

def get_fukusho(row):
    num = row['horse_number']
    if num == row['horse_number_first']:
        return row['hukusyo_first']
    elif num == row['horse_number_second']:
        return row['hukusyo_second']
    elif num == row['horse_number_third']:
        return row['hukusyo_third']
    else:
        return 0  # 異常系（3着以内だけど複勝に該当しない）

# fukusho払い戻しの取得
hits.loc[:, 'fukusho_return'] = hits.apply(get_fukusho, axis=1)

# 投資額・払い戻し合計
total_bets = len(bets) * 1000
hits.loc[:, 'fukusho_return'] = pd.to_numeric(hits['fukusho_return'], errors='coerce').fillna(0)
total_returns = hits['fukusho_return'].sum() * 10  # 100円→1000円単位

print(f"購入数: {len(bets)}件")
print(f"的中数: {len(hits)}件")
print(f"投資額: {total_bets}円")
print(f"払戻額: {total_returns}円")
print(f"収支: {total_returns - total_bets}円")
print(f"回収率: {total_returns / total_bets:.2%}")

# test_data を CSV に保存（グラフ作成や分析用）
test_data.to_csv("cleaned_test_data.csv", index=False)
