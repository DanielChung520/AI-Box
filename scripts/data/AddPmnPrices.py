#!/usr/bin/env python3
"""
為 pmn_file 採購單身檔增加模擬單價 (pmn09)
單價與料號主檔 (ima27) 差異在 ±10% 以內
創建日期: 2026-02-08
"""

import json
import hashlib
import random
import datetime

# 讀取料號主檔單價
def load_item_prices():
    with open("/home/daniel/ai-box/scripts/data/ima_with_prices.json", "r") as f:
        return json.load(f)


def generate_purchase_price(ima01: str, standard_price: float) -> float:
    """根據料號生成採購單價，與標準單價差異 ±10%"""
    # 使用料號作為 seed，確保同一料號每次生成的價格一致
    hash_val = int(hashlib.md5(ima01.encode()).hexdigest(), 16)
    random.seed(hash_val)
    
    # 差異範圍: -10% 到 +10%
    variance = random.uniform(-0.10, 0.10)
    purchase_price = round(standard_price * (1 + variance), 2)
    
    return purchase_price


def generate_pmn_records(item_prices, records_per_item=3):
    """生成 pmn_file 採購單身檔記錄"""
    pmn_records = []
    
    # 採購單號前綴
    po_prefixes = ["PO-202401", "PO-202402", "PO-202403"]
    
    for idx, item in enumerate(item_prices):
        ima01 = item["ima01"]
        standard_price = item["ima27"]
        
        # 為每個料號生成多筆採購記錄
        for rec_idx in range(records_per_item):
            # 生成採購單號
            po_number = f"{po_prefixes[rec_idx]}{str(idx % 9999).zfill(4)}"
            
            # 生成採購單價 (±10% 差異)
            purchase_price = generate_purchase_price(ima01, standard_price)
            
            # 生成採購數量 (100-10000)
            hash_val = int(hashlib.md5(f"{ima01}{rec_idx}".encode()).hexdigest(), 16)
            random.seed(hash_val)
            qty = random.randint(100, 10000)
            
            # 生成已交數量 (0-qty)
            delivered_qty = random.randint(0, qty)
            
            # 生成預計到貨日
            base_date = datetime.date(2024, 1, 1)
            days_ahead = random.randint(0, 180)
            arrival_date = base_date + datetime.timedelta(days=days_ahead)
            
            pmn_records.append({
                "pmn01": po_number,
                "pmn02": rec_idx + 1,
                "pmn04": ima01,
                "pmn09": purchase_price,  # 採購單價
                "pmn20": qty,
                "pmn31": delivered_qty,
                "pmn33": arrival_date.strftime("%Y-%m-%d")
            })
    
    return pmn_records


def main():
    print("=" * 70)
    print("生成 pmn_file 採購單身檔（含單價 pmn09）")
    print("=" * 70)
    
    # 讀取料號單價
    item_prices = load_item_prices()
    print(f"\n📦 料號數量: {len(item_prices)}")
    
    # 生成 pmn 記錄
    pmn_records = generate_pmn_records(item_prices, records_per_item=3)
    
    print(f"📋 生成的採購記錄數: {len(pmn_records)}")
    
    # 保存 JSON
    output_file = "/home/daniel/ai-box/scripts/data/pmn_with_prices.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(pmn_records, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已保存: {output_file}")
    
    # 顯示樣本
    print()
    print("=" * 70)
    print("📊 樣本資料（顯示單價與標準單價對比）")
    print("=" * 70)
    
    # 建立價格對照表
    price_map = {item["ima01"]: item["ima27"] for item in item_prices}
    
    print(f"\n{'採購單號':15} | {'料號':10} | {'標準單價':>10} | {'採購單價':>10} | {'差異%':>8} | {'數量':>6}")
    print("-" * 80)
    
    for rec in pmn_records[:15]:
        ima01 = rec["pmn04"]
        std_price = price_map.get(ima01, 0)
        purchase_price = rec["pmn09"]
        
        if std_price > 0:
            diff_pct = (purchase_price - std_price) / std_price * 100
            diff_str = f"{diff_pct:+.1f}%"
        else:
            diff_str = "N/A"
        
        print(f"{rec['pmn01']:15} | {ima01:10} | {std_price:>10.2f} | {purchase_price:>10.2f} | {diff_str:>8} | {rec['pmn20']:>6}")
    
    # 統計
    print()
    print("=" * 70)
    print("📈 統計資料")
    print("=" * 70)
    
    total_records = len(pmn_records)
    items_with_data = len(set(rec["pmn04"] for rec in pmn_records))
    
    # 計算差異百分比
    price_variances = []
    for rec in pmn_records:
        ima01 = rec["pmn04"]
        std_price = price_map.get(ima01, 0)
        if std_price > 0:
            variance = abs(rec["pmn09"] - std_price) / std_price * 100
            price_variances.append(variance)
    
    avg_variance = sum(price_variances) / len(price_variances) if price_variances else 0
    max_variance = max(price_variances) if price_variances else 0
    
    print(f"\n總採購記錄數: {total_records}")
    print(f"涉及料號數量: {items_with_data}")
    print(f"平均單價差異: {avg_variance:.2f}%")
    print(f"最大單價差異: {max_variance:.2f}%")
    
    # 驗證差異範圍
    within_10pct = sum(1 for v in price_variances if v <= 10)
    print(f"\n差異 ≤ 10% 的筆數: {within_10pct} / {len(price_variances)} ({within_10pct/len(price_variances)*100:.1f}%)")
    
    print()
    print("=" * 70)
    print("✅ 模擬資料生成完成")
    print("=" * 70)
    
    return pmn_records


if __name__ == "__main__":
    main()
