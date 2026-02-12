#!/usr/bin/env python3
"""
在 ima_file 料號主檔中增加模擬單價欄位 (ima27)
創建日期: 2026-02-08
"""

import json
import hashlib
import random

# 料號列表（從 Data-Agent 查詢獲得）
ITEMS = [
    # 成品 (M) - 較高單價
    {"ima01": "10-0001", "ima08": "M"},
    {"ima01": "10-0002", "ima08": "M"},
    {"ima01": "10-0003", "ima08": "M"},
    {"ima01": "10-0004", "ima08": "M"},
    {"ima01": "10-0005", "ima08": "M"},
    {"ima01": "10-0006", "ima08": "M"},
    {"ima01": "10-0007", "ima08": "M"},
    {"ima01": "10-0008", "ima08": "M"},
    {"ima01": "10-0009", "ima08": "M"},
    {"ima01": "10-0010", "ima08": "M"},
    {"ima01": "10-0011", "ima08": "M"},
    {"ima01": "10-0012", "ima08": "M"},
    {"ima01": "10-0013", "ima08": "M"},
    {"ima01": "10-0014", "ima08": "M"},
    {"ima01": "10-0015", "ima08": "M"},
    {"ima01": "10-0016", "ima08": "M"},
    {"ima01": "10-0017", "ima08": "M"},
    {"ima01": "10-0018", "ima08": "M"},
    {"ima01": "10-0019", "ima08": "M"},
    {"ima01": "10-0020", "ima08": "M"},
]

# 原料 (P) - 較低單價
RAW_MATERIALS = [
    ("RM01-", "鋁合金錠", (50, 200)),
    ("RM02-", "不鏽鋼板", (80, 300)),
    ("RM03-", "鍍鋅鋼捲", (60, 250)),
    ("RM04-", "精密螺絲", (5, 50)),
    ("RM05-", "散熱膏", (20, 100)),
    ("RM06-", "烤漆塗料", (80, 200)),
    ("RM07-", "包裝紙箱", (10, 50)),
    ("RM08-", "防震膠墊", (15, 60)),
    ("RM09-", "銅質墊片", (30, 120)),
    ("RM10-", "塑料件", (5, 40)),
]

# 生成固定隨機價格（基於料號的 hash，確保每次執行結果一致）
def generate_price(ima01: str, item_type: str, price_range: tuple) -> float:
    """根據料號生成固定的隨機價格"""
    hash_val = int(hashlib.md5(ima01.encode()).hexdigest(), 16)
    random.seed(hash_val)
    min_price, max_price = price_range
    price = round(random.uniform(min_price, max_price), 2)
    return price


def main():
    """生成帶單價的料號資料"""

    # 1. 生成成品價格 (100-5000)
    print("=" * 70)
    print("生成模擬單價資料")
    print("=" * 70)
    print()
    print("01. 成品 (M) - 單價範圍: 100-5000")
    print("-" * 70)
    print(f"{'料號':12} | {'單價':>10} | {'類型'}")
    print("-" * 70)

    items_with_prices = []

    for item in ITEMS:
        ima01 = item["ima01"]
        price = generate_price(ima01, "M", (100, 5000))
        items_with_prices.append({
            "ima01": ima01,
            "ima27": price,
            "ima08": "M"
        })
        print(f"{ima01:12} | {price:>10.2f} | 成品")

    # 2. 生成原料價格
    print()
    print("02. 原料 (P) - 各類原料單價範圍不同")
    print("-" * 70)

    for prefix, name, price_range in RAW_MATERIALS:
        print(f"\n{prefix}xxx - {name} (單價範圍: {price_range[0]}-{price_range[1]})")
        for i in range(1, 11):
            ima01 = f"{prefix}{str(i).zfill(3)}"
            price = generate_price(ima01, "P", price_range)
            items_with_prices.append({
                "ima01": ima01,
                "ima27": price,
                "ima08": "P"
            })
            print(f"  {ima01:10} | {price:>10.2f}")

    # 3. 保存為 JSON 檔案
    output_file = "/home/daniel/ai-box/scripts/data/ima_with_prices.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(items_with_prices, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 70)
    print(f"✅ 模擬單價資料已生成：{output_file}")
    print(f"   總筆數: {len(items_with_prices)}")
    print("=" * 70)

    # 4. 統計
    m_items = [i for i in items_with_prices if i["ima08"] == "M"]
    p_items = [i for i in items_with_prices if i["ima08"] == "P"]

    print()
    print("📊 單價統計：")
    print(f"   成品 (M): {len(m_items)} 筆, 平均 ${sum(i['ima27'] for i in m_items)/len(m_items):.2f}")
    print(f"   原料 (P): {len(p_items)} 筆, 平均 ${sum(i['ima27'] for i in p_items)/len(p_items):.2f}")


if __name__ == "__main__":
    main()
