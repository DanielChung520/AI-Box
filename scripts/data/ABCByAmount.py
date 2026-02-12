#!/usr/bin/env python3
"""
ABC 分類分析 - 金額佔比版本
創建日期: 2026-02-08
"""

import json
import random
import hashlib


def main():
    # 讀取模擬資料
    with open("/home/daniel/ai-box/scripts/data/ima_with_prices.json", "r") as f:
        ima_prices = json.load(f)
    
    with open("/home/daniel/ai-box/scripts/data/pmn_with_prices.json", "r") as f:
        pmn_data = json.load(f)
    
    # 建立價格對照表
    ima_price_map = {item["ima01"]: item["ima27"] for item in ima_prices}
    
    print("=" * 85)
    print(" 📦 ABC 分類分析 - 金額佔比版本")
    print("=" * 85)
    
    # 生成模擬庫存數據
    img_inventory = []
    for item in ima_prices:
        ima01 = item["ima01"]
        hash_val = int(hashlib.md5(ima01.encode()).hexdigest(), 16)
        random.seed(hash_val)
        qty = random.randint(50000, 2000000)
        img_inventory.append({
            "ima01": ima01,
            "總數量": qty
        })
    
    # 獲取最新採購單價
    pmn_latest = {}
    for rec in pmn_data:
        ima01 = rec["pmn04"]
        if ima01 not in pmn_latest:
            pmn_latest[ima01] = rec["pmn09"]
    
    # Join 計算庫存價值
    inventory = []
    for inv in img_inventory:
        ima01 = inv["ima01"]
        qty = inv["總數量"]
        price = pmn_latest.get(ima01, ima_price_map.get(ima01, 0))
        value = qty * price
        inventory.append({
            "ima01": ima01,
            "總數量": qty,
            "單價": price,
            "總價值": value
        })
    
    # 按價值排序
    inventory.sort(key=lambda x: x["總價值"], reverse=True)
    
    # 計算總價值和累積
    total_value = sum(item["總價值"] for item in inventory)
    cumsum = 0
    
    def classify(cum_pct):
        if cum_pct <= 70: return 'A'
        elif cum_pct <= 90: return 'B'
        else: return 'C'
    
    print()
    print("=" * 85)
    print(" 📊 ABC 分類結果（金額佔比）")
    print("=" * 85)
    print()
    print("說明：A 類 = 累積金額前 70%，B 類 = 70%~90%，C 類 = 90%~100%")
    print()
    print("-" * 105)
    print(" 排名 |  料號    |   庫存數量  |   單價   |     總價值        | 金額佔比 | 累積%  | ABC")
    print("-" * 105)
    
    a_items, b_items, c_items = [], [], []
    
    for idx, item in enumerate(inventory, 1):
        cumsum += item["總價值"]
        pct = round(item["總價值"] / total_value * 100, 2) if total_value > 0 else 0
        cum_pct = round(cumsum / total_value * 100, 2) if total_value > 0 else 0
        abc = classify(cum_pct)
        
        if abc == 'A': a_items.append(item)
        elif abc == 'B': b_items.append(item)
        else: c_items.append(item)
        
        if idx <= 25 or abc == 'A' or (abc == 'B' and len(b_items) <= 5) or abc == 'C':
            print(f" {idx:3}  | {item['ima01']:10} | {item['總數量']:>12,} | {item['單價']:>8.2f} | {item['總價值']:>18,.2f} |  {pct:>5.1f}%  | {cum_pct:>5.1f}%  |  {abc}")
    
    print("-" * 105)
    
    # 統計
    a_value = sum(item["總價值"] for item in a_items)
    b_value = sum(item["總價值"] for item in b_items)
    c_value = sum(item["總價值"] for item in c_items)
    
    print()
    print("=" * 85)
    print(" 📈 ABC 分類統計（金額佔比）")
    print("=" * 85)
    print()
    print(f" 總庫存價值: ${total_value:,.2f}")
    print()
    print(f" 類別 |  料號數量  |  料號佔比  |     金額      |  金額佔比  |      管理策略")
    print("-" * 85)
    print(f"  A   |   {len(a_items):4}    |   {len(a_items)/len(inventory)*100:5.1f}%   | ${a_value:>14,.2f} |  {a_value/total_value*100:>5.1f}%  |  重點管理 (安全庫存、多源供應)")
    print(f"  B   |   {len(b_items):4}    |   {len(b_items)/len(inventory)*100:5.1f}%   | ${b_value:>14,.2f} |  {b_value/total_value*100:>5.1f}%  |  適度關注 (定期盤點、彈性採購)")
    print(f"  C   |   {len(c_items):4}    |   {len(c_items)/len(inventory)*100:5.1f}%   | ${c_value:>14,.2f} |  {c_value/total_value*100:>5.1f}%  |  簡化管理 (減少庫存、JIT 採購)")
    print("-" * 85)
    
    # 金額佔比驗證
    print()
    print("=" * 85)
    print(" 📋 金額佔比驗證")
    print("=" * 85)
    print()
    print(f"  A 類金額佔比: {a_value/total_value*100:.1f}% (目標: 70%)")
    print(f"  B 類金額佔比: {b_value/total_value*100:.1f}% (目標: 20%)")
    print(f"  C 類金額佔比: {c_value/total_value*100:.1f}% (目標: 10%)")
    print(f"  總計:        {(a_value+b_value+c_value)/total_value*100:.1f}%")
    
    # 單價驗證
    print()
    print("=" * 85)
    print(" 📋 單價一致性驗證（與標準單價 ima27 差異 ±10%）")
    print("=" * 85)
    print()
    
    price_diffs = []
    seen_items = set()
    for rec in pmn_data:
        ima01 = rec["pmn04"]
        if ima01 in seen_items:
            continue
        seen_items.add(ima01)
        
        std_price = ima_price_map.get(ima01, 0)
        pmn_price = rec["pmn09"]
        if std_price > 0:
            diff = abs((pmn_price - std_price) / std_price * 100)
            price_diffs.append(diff)
    
    if price_diffs:
        print(f"  平均差異: {sum(price_diffs)/len(price_diffs):.2f}%")
        print(f"  最大差異: {max(price_diffs):.2f}%")
        within_10 = sum(1 for p in price_diffs if p <= 10)
        print(f"  差異 ≤ 10%: {within_10}/{len(price_diffs)} ({within_10/len(price_diffs)*100:.1f}%)")
    
    print()
    print("=" * 85)
    print("✅ ABC 分類分析完成")
    print("=" * 85)


if __name__ == "__main__":
    main()
