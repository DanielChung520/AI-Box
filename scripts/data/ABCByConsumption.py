#!/usr/bin/env python3
"""
ABC 分類分析 - 按年度消耗量
使用 pmn_file 採購資料模擬年度消耗量

創建日期: 2026-02-08
"""

import json
import random
import hashlib
from datetime import datetime, timedelta


def main():
    # 讀取模擬資料
    with open("/home/daniel/ai-box/scripts/data/ima_with_prices.json", "r") as f:
        ima_prices = json.load(f)
    
    with open("/home/daniel/ai-box/scripts/data/pmn_with_prices.json", "r") as f:
        pmn_data = json.load(f)
    
    # 建立價格對照表
    ima_price_map = {item["ima01"]: item["ima27"] for item in ima_prices}
    
    print("=" * 85)
    print(" 📦 ABC 分類分析 - 按年度消耗量")
    print("=" * 85)
    print()
    print("說明：使用 pmn_file 採購資料模擬年度消耗量")
    print("      消耗量 = 各筆採購數量 (pmn20) 之總和")
    print("      消耗價值 = 消耗量 × 單價 (pmn09)")
    
    # Step 1: 計算每個料號的年度消耗量
    print()
    print("=" * 85)
    print("【步驟 1】計算年度消耗量")
    print("-" * 85)
    
    # 統計每個料號的總消耗量
    consumption = {}
    for rec in pmn_data:
        ima01 = rec["pmn04"]
        qty = rec.get("pmn20", 0)
        price = rec.get("pmn09", 0)
        
        if ima01 not in consumption:
            consumption[ima01] = {
                "總消耗數量": 0,
                "採購次數": 0,
                "單價": price,
                "標準單價": ima_price_map.get(ima01, 0)
            }
        
        consumption[ima01]["總消耗數量"] += qty
        consumption[ima01]["採購次數"] += 1
    
    # 計算消耗價值
    for ima01, data in consumption.items():
        data["消耗價值"] = data["總消耗數量"] * data["單價"]
    
    # 轉換為列表並排序
    consumption_list = []
    for ima01, data in consumption.items():
        consumption_list.append({
            "料號": ima01,
            "總消耗數量": data["總消耗數量"],
            "採購次數": data["採購次數"],
            "單價": data["單價"],
            "標準單價": data["標準單價"],
            "消耗價值": data["消耗價值"]
        })
    
    # 按消耗價值排序
    consumption_list.sort(key=lambda x: x["消耗價值"], reverse=True)
    
    print(f"  總料號數: {len(consumption_list)}")
    print(f"  總消耗價值: ${sum(x['消耗價值'] for x in consumption_list):,.2f}")
    
    # Step 2: ABC 分類
    print()
    print("=" * 85)
    print("【步驟 2】ABC 分類結果（按年度消耗量）")
    print("=" * 85)
    print()
    print("說明：A 類 = 累積消耗價值前 70%，B 類 = 70%~90%，C 類 = 90%~100%")
    print()
    
    total_value = sum(x["消耗價值"] for x in consumption_list)
    cumsum = 0
    
    def classify(cum_pct):
        if cum_pct <= 70: return 'A'
        elif cum_pct <= 90: return 'B'
        else: return 'C'
    
    print("-" * 110)
    print(" 排名 |  料號    | 年度消耗數量 |   單價   |     消耗價值        | 價值佔比 | 累積%  | ABC")
    print("-" * 110)
    
    a_items, b_items, c_items = [], [], []
    
    for idx, item in enumerate(consumption_list, 1):
        cumsum += item["消耗價值"]
        pct = round(item["消耗價值"] / total_value * 100, 2) if total_value > 0 else 0
        cum_pct = round(cumsum / total_value * 100, 2) if total_value > 0 else 0
        abc = classify(cum_pct)
        
        if abc == 'A': a_items.append(item)
        elif abc == 'B': b_items.append(item)
        else: c_items.append(item)
        
        # 顯示所有 A 類、B 類前5筆、C 類前5筆
        if abc == 'A' or (abc == 'B' and len(b_items) <= 5) or (abc == 'C' and len(c_items) <= 5):
            print(f" {idx:4} | {item['料號']:10} | {item['總消耗數量']:>12,} | {item['單價']:>8.2f} | {item['消耗價值']:>18,.2f} |  {pct:>5.1f}% | {cum_pct:>5.1f}% |  {abc}")
    
    print("-" * 110)
    
    # Step 3: 統計
    print()
    print("=" * 85)
    print("【步驟 3】ABC 分類統計")
    print("=" * 85)
    
    a_value = sum(x["消耗價值"] for x in a_items)
    b_value = sum(x["消耗價值"] for x in b_items)
    c_value = sum(x["消耗價值"] for x in c_items)
    
    print()
    print(" 類別 |  料號數量  |  料號佔比  |     消耗價值      |  價值佔比  |      管理策略")
    print("-" * 85)
    print(f"  A   |   {len(a_items):4}    |   {len(a_items)/len(consumption_list)*100:5.1f}%   | ${a_value:>14,.2f} |  {a_value/total_value*100:>5.1f}%  |  重點管理 (安全庫存、多源供應)")
    print(f"  B   |   {len(b_items):4}    |   {len(b_items)/len(consumption_list)*100:5.1f}%   | ${b_value:>14,.2f} |  {b_value/total_value*100:>5.1f}%  |  適度關注 (定期盤點、彈性採購)")
    print(f"  C   |   {len(c_items):4}    |   {len(c_items)/len(consumption_list)*100:5.1f}%   | ${c_value:>14,.2f} |  {c_value/total_value*100:>5.1f}%  |  簡化管理 (減少庫存、JIT 採購)")
    print("-" * 85)
    
    # Step 4: 與庫存價值比較
    print()
    print("=" * 85)
    print("【步驟 4】消耗量 ABC vs 庫存價值 ABC 比較")
    print("=" * 85)
    
    # 計算庫存價值
    img_inventory = []
    for item in ima_prices:
        ima01 = item["ima01"]
        hash_val = int(hashlib.md5(ima01.encode()).hexdigest(), 16)
        random.seed(hash_val)
        qty = random.randint(50000, 2000000)
        img_inventory.append({
            "ima01": ima01,
            "總數量": qty,
            "單價": item["ima27"],
            "庫存價值": qty * item["ima27"]
        })
    
    img_inventory.sort(key=lambda x: x["庫存價值"], reverse=True)
    
    # 計算庫存 ABC
    total_inv = sum(x["庫存價值"] for x in img_inventory)
    inv_cumsum = 0
    inv_a, inv_b, inv_c = [], [], []
    
    for item in img_inventory:
        inv_cumsum += item["庫存價值"]
        pct = inv_cumsum / total_inv * 100
        abc = classify(pct)
        if abc == 'A': inv_a.append(item)
        elif abc == 'B': inv_b.append(item)
        else: inv_c.append(item)
    
    print()
    print("                    |   消耗量 ABC   |   庫存價值 ABC")
    print("-" * 65)
    print(f"  A 類料號數         |      {len(a_items):3}       |       {len(inv_a):3}")
    print(f"  A 類金額佔比        |    {a_value/total_value*100:5.1f}%      |     {sum(x['庫存價值'] for x in inv_a)/total_inv*100:.1f}%")
    print(f"  B 類料號數         |      {len(b_items):3}       |       {len(inv_b):3}")
    print(f"  B 類金額佔比        |    {b_value/total_value*100:5.1f}%      |     {sum(x['庫存價值'] for x in inv_b)/total_inv*100:.1f}%")
    print(f"  C 類料號數         |      {len(c_items):3}       |       {len(inv_c):3}")
    print(f"  C 類金額佔比        |    {c_value/total_value*100:5.1f}%      |     {sum(x['庫存價值'] for x in inv_c)/total_inv*100:.1f}%")
    
    # Step 5: 找出差異
    print()
    print("=" * 85)
    print("【步驟 5】分類差異分析")
    print("=" * 85)
    
    consumption_abc = set(x["料號"] for x in a_items + b_items + c_items)
    inventory_abc = set(x["ima01"] for x in inv_a + inv_b + inv_c)
    
    a_consumption = set(x["料號"] for x in a_items)
    a_inventory = set(x["ima01"] for x in inv_a)
    
    only_consumption_a = a_consumption - a_inventory
    only_inventory_a = a_inventory - a_consumption
    
    print()
    print(f"  A 類差異：")
    print(f"    僅在消耗量 A 類: {only_consumption_a if only_consumption_a else '無'}")
    print(f"    僅在庫存價值 A 類: {only_inventory_a if only_inventory_a else '無'}")
    
    print()
    print("=" * 85)
    print("✅ ABC 分類分析完成（按年度消耗量）")
    print("=" * 85)


if __name__ == "__main__":
    main()
