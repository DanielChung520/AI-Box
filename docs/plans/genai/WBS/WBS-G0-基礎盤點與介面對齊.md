<!--
代碼功能說明: WBS-G0 基礎盤點與介面對齊
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G0：基礎盤點與介面對齊

## 目標

把「前端輸入框 → 模型（Auto/收藏） → 上下文/記憶」這條產品鏈路所需的**接口、資料結構、追蹤點**先定稿，避免後續反覆重構。

## 工作項

- **G0.1 產品入口 API 定義**
  - 定義 Chat Request/Response schema（messages、session_id、task_id、model_selector、attachments）
  - 定義 error code 與可回報的 observability fields

- **G0.2 Auto / 收藏模型選擇規格**
  - Auto：需要 task_classification 的來源與格式
  - 收藏：user preference 儲存位置（MVP：localStorage 或 ArangoDB）

- **G0.3 Context/Memory 介面對齊**
  - session_id 生成/傳遞規則
  - ContextWindow 截斷策略（max_tokens / max_messages）
  - Memory retrieval 注入格式（system prompt / tool context / citations）

- **G0.4 觀測指標最小集合**
  - routing_decision（provider/model/strategy）
  - latency、token/cost（若可得）
  - memory_hit（命中數、來源、top-k）

## 驗收

- 有一份可執行的 API 契約（前後端一致）
- Auto/收藏/Context/Memory 的資料結構確定
- 指標欄位確定
