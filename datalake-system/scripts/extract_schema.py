import pandas as pd
import json
import os
from pathlib import Path


def extract_schemas(excel_path, output_dir):
    print(f"正在讀取 Excel: {excel_path}")
    df = pd.read_excel(excel_path, sheet_name="Sheet1")

    # 定義我們想要鎖定的標準表名與關鍵字
    target_mappings = {
        "ima_file": ["ITEM", "物料"],
        "pmc_file": ["PMC", "供應商"],
        "imd_file": ["WAREHOUSE", "倉庫"],
        "ime_file": ["IME", "儲位"],
        "pmm_file": ["PURMM", "採購單頭"],
        "pmn_file": ["PURMN", "採購單身"],
        "tlf_file": ["TLF", "異動", "過帳"],
        "img_file": ["IMG", "庫存", "餘額"],
    }

    schemas = {}

    for table_name, keywords in target_mappings.items():
        print(f"正在尋找表: {table_name} ...")
        # 匹配邏輯：檔案代碼包含關鍵字[0] OR 檔案名稱包含關鍵字[1]
        mask = df["檔案代碼"].str.contains(keywords[0], na=False, case=False) | df[
            "檔案名稱"
        ].str.contains(keywords[1], na=False)

        table_cols = df[mask].copy()

        if table_cols.empty:
            print(f"⚠️ 找不到匹配的資料: {table_name}")
            continue

        # 移除重複欄位（選取第一個出現的檔案代碼的結構）
        representative_code = table_cols["檔案代碼"].iloc[0]
        final_cols = table_cols[table_cols["檔案代碼"] == representative_code]

        column_list = []
        for _, row in final_cols.iterrows():
            column_list.append(
                {
                    "id": str(row["欄位編號"]).strip(),
                    "name": str(row["欄位名稱"]).strip(),
                    "type": str(row["型態"]).strip(),
                    "length": float(row["長度"]) if not pd.isna(row["長度"]) else 0,
                    "description": str(row["欄位說明"]).strip(),
                }
            )

        schemas[table_name] = {
            "canonical_name": table_name,
            "tiptop_code": representative_code,
            "tiptop_name": str(final_cols["檔案名稱"].iloc[0]),
            "columns": column_list,
        }
        print(f"✅ 成功提取 {table_name} ({len(column_list)} 個欄位)")

    # 存檔
    output_path = Path(output_dir) / "schema_registry.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schemas, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 所有 Schema 已導出至: {output_path}")


if __name__ == "__main__":
    EXCEL_PATH = "/Users/daniel/GitHub/AI-Box/docs/Tiptop.xlsx"
    OUTPUT_DIR = "/Users/daniel/GitHub/AI-Box/datalake-system/metadata"
    extract_schemas(EXCEL_PATH, OUTPUT_DIR)
