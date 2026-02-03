import pandas as pd
import sys


def analyze_tiptop(file_path):
    try:
        df = pd.read_excel(file_path, sheet_name="Sheet1")

        # 定義關鍵字
        keywords = {
            "庫存/倉儲": ["庫存", "倉儲", "入庫", "出庫", "調撥", "盤點"],
            "料號/物料": ["料號", "物料", "品名", "規格", "BOM", "主檔"],
            "採購": ["採購", "請購", "驗收", "收料", "供應商"],
        }

        results = {}

        for category, kws in keywords.items():
            # 建立過濾條件：檔案名稱或欄位說明包含關鍵字
            pattern = "|".join(kws)
            mask = df["檔案名稱"].str.contains(pattern, na=False) | df["欄位說明"].str.contains(
                pattern, na=False
            )
            filtered_df = df[mask]

            # 取得不重複的檔案代碼與檔案名稱
            tables_df = filtered_df[["檔案代碼", "檔案名稱"]].drop_duplicates()
            tables = tables_df.values.tolist()
            results[category] = tables

        # 輸出結果
        for category, tables in results.items():
            print(f"\n===== 【{category}】 相關資料表 (共 {len(tables)} 個) =====")
            # 顯示前 15 個最重要的
            for code, name in tables[:15]:
                print(f"[{code}] {name}")
            if len(tables) > 15:
                print(f"... 以及其他 {len(tables) - 15} 個資料表")

    except Exception as e:
        print(f"分析失敗: {e}")


if __name__ == "__main__":
    file_path = "/home/daniel/ai-box/docs/Tiptop.xlsx"
    analyze_tiptop(file_path)
