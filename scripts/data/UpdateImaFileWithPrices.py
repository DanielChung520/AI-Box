#!/usr/bin/env python3
"""
使用 DuckDB 將模擬單價寫入 ima_file Parquet 檔案
創建日期: 2026-02-08
"""

import json
import duckdb
import os

def main():
    # 讀取模擬單價資料
    with open("/home/daniel/ai-box/scripts/data/ima_with_prices.json", "r") as f:
        prices = json.load(f)

    # 建立 price lookup dict
    price_dict = {item["ima01"]: item["ima27"] for item in prices}

    # 連接 DuckDB
    conn = duckdb.connect(database=":memory:")

    # 註冊價格資料為虛擬表
    conn.register("price_data", prices)

    # 查詢現有 ima_file 結構
    print("=" * 70)
    print("步驟 1: 查看現有 ima_file 結構")
    print("=" * 70)

    result = conn.execute("""
        SELECT * FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet')
        LIMIT 3
    """).fetchall()

    print(f"現有欄位數: {len(result[0]) if result else 0}")
    print(f"總筆數: {conn.execute(\"SELECT COUNT(*) FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet')\").fetchone()[0]}")

    # 步驟 2: 查詢並驗證價格資料
    print()
    print("=" * 70)
    print("步驟 2: 驗證價格資料")
    print("=" * 70)

    price_check = conn.execute("""
        SELECT COUNT(*) as cnt FROM price_data
    """).fetchone()[0]
    print(f"價格資料筆數: {price_check}")

    # 步驟 3: 建立新資料（加入單價）
    print()
    print("=" * 70)
    print("步驟 3: 生成新資料（含單價）")
    print("=" * 70)

    # 由於無法直接修改 S3 Parquet，我們創建一個視圖和導出腳本
    create_view_sql = f"""
        CREATE OR REPLACE VIEW ima_file_with_prices AS
        SELECT 
            ima.*,
            COALESCE(p.ima27, 0) as ima27
        FROM read_parquet('s3://tiptop-raw/raw/v1/ima_file/year=*/month=*/data.parquet') ima
        LEFT JOIN price_data p ON ima.ima01 = p.ima01
    """

    conn.execute(create_view_sql)

    # 驗證視圖
    view_check = conn.execute("SELECT COUNT(*) FROM ima_file_with_prices").fetchone()[0]
    print(f"視圖筆數: {view_check}")

    # 顯示樣本
    print()
    print("樣本資料（含單價）：")
    print("-" * 70)
    sample = conn.execute("""
        SELECT ima01, ima02, ima08, ima27 
        FROM ima_file_with_prices 
        WHERE ima08 = 'M'
        LIMIT 5
    """).fetchall()

    print(f"{'料號':12} | {'品名':20} | {'類型':4} | {'單價':>10}")
    print("-" * 70)
    for row in sample:
        print(f"{row[0]:12} | {row[1][:20]:20} | {row[2]:4} | {row[3]:>10.2f}")

    # 步驟 4: 生成 SQL 查詢語句供後續使用
    print()
    print("=" * 70)
    print("步驟 4: 可使用的查詢語句")
    print("=" * 70)

    print("""
-- 方法 1: 使用視圖查詢（含單價的料號）
SELECT ima01, ima02, ima27 
FROM ima_file_with_prices
WHERE ima27 > 0
LIMIT 10;

-- 方法 2: LEFT JOIN 查詢（庫存價值分析）
SELECT 
    img.img01,
    SUM(img.img10) as 總數量,
    MAX(ima.ima27) as 單價,
    SUM(img.img10) * MAX(ima.ima27) as 總價值
FROM img_file img
LEFT JOIN ima_file_with_prices ima ON img.img01 = ima.ima01
GROUP BY img.img01
ORDER BY 總價值 DESC
LIMIT 20;
""")

    # 步驟 5: 測試 ABC 分類查詢
    print()
    print("=" * 70)
    print("步驟 5: 測試 ABC 分類查詢")
    print("=" * 70)

    abc_query = """
        WITH inventory AS (
            SELECT 
                img.img01,
                SUM(img.img10) as 總數量,
                COALESCE(MAX(ima.ima27), 0) as 單價,
                SUM(img.img10) * COALESCE(MAX(ima.ima27), 0) as 總價值
            FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet') img
            LEFT JOIN (
                SELECT ima01, ima27 FROM price_data
            ) ima ON img.img01 = ima.ima01
            GROUP BY img.img01
        )
        SELECT 
            料號,
            總數量,
            單價,
            總價值,
            ROUND(總價值 * 100.0 / SUM(總價值) OVER(), 2) as 佔比,
            ROUND(SUM(總價值) OVER (ORDER BY 總價值 DESC) * 100.0 / SUM(總價值) OVER(), 2) as 累積佔比
        FROM inventory
        ORDER BY 總價值 DESC
        LIMIT 15
    """

    abc_result = conn.execute(abc_query).fetchall()

    def classify(pct):
        if pct <= 70: return 'A'
        elif pct <= 90: return 'B'
        else: return 'C'

    print()
    print("料號       |   庫存數量  |    單價    |    總價值  | 佔比  | 累積% | ABC")
    print("-" * 90)

    for row in abc_result:
        abc = classify(row[5])
        print(f"{row[0]:10} | {row[1]:>10,} | {row[2]:>10.2f} | {row[3]:>10,.2f} | {row[4]:>5.1f}% | {row[5]:>5.1f}% |  {abc}")

    # 統計
    total_value = conn.execute("""
        WITH inventory AS (
            SELECT 
                SUM(img.img10) * COALESCE(MAX(ima.ima27), 0) as 總價值
            FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet') img
            LEFT JOIN price_data ima ON img.img01 = ima.ima01
            GROUP BY img.img01
        )
        SELECT SUM(總價值) FROM inventory
    """).fetchone()[0]

    print()
    print("=" * 70)
    print("📊 ABC 分類測試完成")
    print(f"   總庫存價值: ${total_value:,.2f}" if total_value else "   無資料")
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()
