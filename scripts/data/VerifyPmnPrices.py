#!/usr/bin/env python3
"""
ABC 分類分析 - 使用模擬資料
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
    
    print("=" * 80)
    print(" 📦 ABC 分類分析 - 使用採購單價 (pmn09)")
    print("=" * 80)
    
    # 生成模擬庫存數據
    print("\n📊 生成模擬庫存數據...")
    
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
    inventory_with_prices = []
    for inv in img_inventory:
        ima01 = inv["ima01"]
        qty = inv["總數量"]
        price = pmn_latest.get(ima01, ima_price_map.get(ima01, 0))
        value = qty * price
        inventory_with_prices.append({
            "ima01": ima01,
            "總數量": qty,
            "單價": price,
            "總價值": value
        })
    
    # 按價值排序
    inventory_with_prices.sort(key=lambda x: x["總價值"], reverse=True)
    
    # 計算 ABC 分類
    total_value = sum(item["總價值"] for item in inventory_with_prices)
    cumsum = 0
    
    def classify(pct):
        if pct <= 70: return 'A'
        elif pct <= 90: return 'B'
        else: return 'C'
    
    print("\n" + "=" * 80)
    print(" 📊 ABC 分類結果（基於採購單價 pmn09）")
    print("=" * 80)
    
    print(f"\n{'料號':12} | {'庫存數量':>14} | {'單價':>8} | {'總價值':>16} | 佔比  | 累積% | ABC")
    print("-" * 90)
    
    a_set, b_set, c_set = set(), set(), set()
    
    for item in inventory_with_prices[:25]:
        cumsum += item["總價值"]
        pct = round(item["總價值"] / total_value * 100, 2) if total_value > 0 else 0
        cum_pct = round(cumsum / total_value * 100, 2) if total_value > 0 else 0
        abc = classify(cum_pct)
        
        if abc == 'A': a_set.add(item["ima01"])
        elif abc == 'B': b_set.add(item["ima01"])
        else: c_set.add(item["ima01"])
        
        print(f"{item['ima01']:12} | {item['總數量']:>14,} | {item['單價']:>8.2f} | {item['總價值']:>16,.2f} | {pct:>5.1f}% | {cum_pct:>5.1f}% |  {abc}")
    
    print("-" * 90)
    print(f"\n📈 ABC 分類統計：")
    print(f"   總庫存價值: ${total_value:,.2f}")
    print(f"   A 類 (累積 70%): {len(a_set):3} 種 ({len(a_set)/len(inventory_with_prices)*100:.1f}%) - 重點管理")
    print(f"   B 類 (70-90%):   {len(b_set):3} 種 ({len(b_set)/len(inventory_with_prices)*100:.1f}%) - 適度關注")
    print(f"   C 類 (90-100%): {len(c_set):3} 種 ({len(c_set)/len(inventory_with_prices)*100:.1f}%) - 簡化管理")
    
    # 單價驗證
    print()
    print("=" * 80)
    print(" 📋 單價一致性驗證（與標準單價 ima27 差異 ±10%）")
    print("=" * 80)
    
    print(f"\n{'料號':12} | {'標準單價':>10} | {'採購單價':>10} | {'差異%':>8}")
    print("-" * 50)
    
    for rec in pmn_data[:8]:
        ima01 = rec["pmn04"]
        std_price = ima_price_map.get(ima01, 0)
        pmn_price = rec["pmn09"]
        if std_price > 0:
            diff = (pmn_price - std_price) / std_price * 100
            print(f"{ima01:12} | {std_price:>10.2f} | {pmn_price:>10.2f} | {diff:>+7.1f}%")
    
    # 統計
    price_diffs = []
    for rec in pmn_data:
        ima01 = rec["pmn04"]
        std_price = ima_price_map.get(ima01, 0)
        pmn_price = rec["pmn09"]
        if std_price > 0:
            diff = abs((pmn_price - std_price) / std_price * 100)
            price_diffs.append(diff)
    
    if price_diffs:
        print()
        print(f"📊 單價差異統計：")
        print(f"   平均差異: {sum(price_diffs)/len(price_diffs):.2f}%")
        print(f"   最大差異: {max(price_diffs):.2f}%")
        within_10 = sum(1 for p in price_diffs if p <= 10)
        print(f"   差異 ≤ 10%: {within_10}/{len(price_diffs)} ({within_10/len(price_diffs)*100:.1f}%)")
    
    print()
    print("=" * 80)
    print("✅ 模擬資料驗證完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
