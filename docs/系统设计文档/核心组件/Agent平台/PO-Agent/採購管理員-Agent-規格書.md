# 採購管理員 Agent 規格書

**版本**：1.0
**創建日期**：2026-01-25
**最後修改日期**：2026-01-25
**適用環境**：AI-Box DataLake (SeaweedFS + Parquet)

---

## 1. 概述

### 1.1 定位
**採購管理員 Agent (Procurement Manager Agent)** 是一位具備商業分析能力的虛擬採購專家。它負責處理企業內部的採購循環數據，提供供應商評價、採購策略建議以及訂單執行進度監控。

**核心目標**：
- ✅ **成本分析**：監控原材料採購價格波動趨勢。
- ✅ **供應商績效**：分析供應商的及時交貨率與供應量占比。
- ✅ **訂單追蹤**：監控「已下單、未收料」的採購單狀態。

### 1.2 架構位置
```
[ 用戶 ] <───> [ Orchestrator ] <───> [ 採購管理員 Agent ]
                                              │
                                              ▼ (Data Access Tool)
                                       [ Data Agent / DataLake ]
```

---

## 2. 工作職責

### 2.1 核心能力清單
1.  **採購歷史查詢 (Purchase History)**：
    *   查詢特定供應商 (`pmm04`) 的採購總額與單據頻率。
    *   分析特定料號 (`pmn04`) 的價格走勢。
2.  **供應商評鑑 (Vendor Performance)**：
    *   統計各供應商的訂單筆數 (`po_count`)。
    *   (未來擴展) 比對「預計到貨日 (`pmn33`)」與「實際收料日 (`tlf06`)」來計算交期偏差。
3.  **採購異常追蹤 (Purchase Exception)**：
    *   找出「已超過到貨日」但「已交數量 (`pmn31`) < 採購數量 (`pmn20`)」的單據。
4.  **成本優化策略 (Strategic Sourcing)**：
    *   針對消耗量大的物料，給出「年度議價 (RFQ)」或「尋找替代商」的建議。

---

## 3. Data Agent 交互規格

採購管理員 Agent 透過以下方式調用 DataLake：

### 3.1 獲取採購與供應商關聯數據
**Action**: `get_purchase_history`
**參數**: `vendor_id` (Optional), `item_id` (Optional)
```python
# 內部邏輯範例
po_data = client.get_purchase_history(vendor_id="VND001")
# 回傳欄位：pmm01(單號), pmm04(供應商), pmn04(料號), pmn20(採購量), pmn33(到貨日)
```

### 3.2 分析收料狀況
**Action**: `query_table`
**參數**: `table_name="rvb_file"`, `filters={"rvb05": "RM01-001"}`
```python
# 查詢特定物料的收料歷史
receipts = client.query_table("rvb_file", filters={"rvb05": "RM01-001"})
```

---

## 4. 業務邏輯判斷 (Business Intelligence)

### 4.1 交期與數量判定
Agent 應具備以下邏輯判斷力：
*   **逾期未交**：`current_date > pmn33` 且 `pmn31 < pmn20`。
*   **價格優勢**：當特定物料的最新單價低於過去半年平均單價 10% 時，主動提示採購優勢。

### 4.2 供應商風險識別
*   **過度依賴風險**：若單一供應商佔特定類別物料採購量 80% 以上，Agent 應回覆：「風險警示：該類物料對供應商 X 的依賴度過高，建議建立第二來源備案。」

---

## 5. 交付與響應標準 (繁體中文)

Agent 應以資深採購主管的口吻回覆：

**用戶問**：「2025 年我們採購最多的是哪家廠？」
**Agent 回覆**：
> 「根據 DataLake 的全年度採購分析：
> 2025 年採購規模最大的供應商是 **達台電子 (VND001)**，
> 全年共下單 **163 筆**，累計供應數量達 **205,109 單位**。
> 主要採購品項集中在『精密沖壓支架』類別。
> 💡 建議：考慮到該商的高貢獻度，建議在 2026 Q1 重啟議價流程以爭取批量折扣。」

---

## 6. 實現計劃

1.  **具體化工具集**：註冊 MCP 工具 `analyze_vendor_performance`, `track_open_orders`。
2.  **數據壓力測試**：確保在 180 筆 PO 單與 1700 筆採購明細的基礎上，具備亞秒級的回覆能力。
3.  **多 Agent 協作**：測試物管 Agent 發現缺料後，轉由採購 Agent 推薦最佳供應商的流程。
