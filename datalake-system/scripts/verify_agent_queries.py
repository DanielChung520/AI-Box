from data_access import DataLakeClient
import pandas as pd


def simulate_agents():
    client = DataLakeClient()
    print("🤖 AI-Box Data Agent 查詢驗證啟動...")
    print("=" * 50)

    # 場景 1: 物料管理員 Agent
    print("\n[場景 1: 物料管理員]")
    print("提問: '請幫我列出目前成品倉(W03)中庫存最高的前 5 個品項。'")

    inv_df = client.get_inventory_status()
    # 過濾成品倉並排序
    w03_top = inv_df[inv_df["img02"] == "W03"].sort_values("img10", ascending=False).head(5)

    print("Agent 解析結果:")
    for _, row in w03_top.iterrows():
        print(f"- 品號: {row['ima01']}, 品名: {row['ima02']}, 數量: {row['img10']} {row['ima25']}")

    # 場景 2: 採購管理員 Agent
    print("\n[場景 2: 採購管理員]")
    print("提問: '最近有哪些供應商的採購次數最多？'")

    po_df = client.get_purchase_history()
    # 統計供應商出現頻率
    vendor_stats = po_df.groupby("pmm04").size().reset_index(name="po_count")
    # 關聯供應商名稱
    vendors = client.query_table("pmc_file")
    top_vendors = (
        pd.merge(vendor_stats, vendors[["pmc01", "pmc03"]], left_on="pmm04", right_on="pmc01")
        .sort_values("po_count", ascending=False)
        .head(3)
    )

    print("Agent 解析結果:")
    for _, row in top_vendors.iterrows():
        print(f"- 供應商: {row['pmc03']} (ID: {row['pmc01']}), 採購單數: {row['po_count']}")

    # 場景 3: 異常監控
    print("\n[場景 3: 庫存異常監控]")
    print("任務: '檢查是否有庫存為負數的異常紀錄。'")
    neg_stock = inv_df[inv_df["img10"] < 0]
    if neg_stock.empty:
        print("✅ 檢查完成: 未發現負庫存異常。")
    else:
        print(f"⚠️ 發現 {len(neg_stock)} 筆異常紀錄！")


if __name__ == "__main__":
    simulate_agents()
