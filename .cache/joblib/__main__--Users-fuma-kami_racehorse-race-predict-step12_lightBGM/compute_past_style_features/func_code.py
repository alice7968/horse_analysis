# first line: 69
@memory.cache
def compute_past_style_features(df, n=5):
    df_sorted = df.sort_values("date")
    style_list = []

    for horse_id, group in df_sorted.groupby("horse_id"):
        group = group.sort_values("date")
        styles = []

        for i, row in group.iterrows():
            past_rows = group[(group["date"] < row["date"]) & (group["half_way_dif"] >= 0)]
            past_rows = past_rows.tail(n)
            if past_rows.empty:
                styles.append({"style_逃げ": 0, "style_先行": 0, "style_差し": 0, "style_追い込み": 0})
                continue

            style_cats = pd.cut(
                past_rows["half_way_dif"] / past_rows["headcount"],
                bins=[0, 0.1, 0.3, 0.7, 1.0],
                labels=["逃げ", "先行", "差し", "追い込み"],
                right=False
            )
            counts = style_cats.value_counts(normalize=True)
            styles.append({
                f"style_逃げ": counts.get("逃げ", 0),
                f"style_先行": counts.get("先行", 0),
                f"style_差し": counts.get("差し", 0),
                f"style_追い込み": counts.get("追い込み", 0),
            })

    style_df = pd.DataFrame(styles, index=df_sorted.index)
    return style_df.sort_index()
