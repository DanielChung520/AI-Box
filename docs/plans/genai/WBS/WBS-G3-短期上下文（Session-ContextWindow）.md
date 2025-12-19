<!--
代碼功能說明: WBS-G3 短期上下文（Session/ContextWindow）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G3：短期上下文（Session / ContextWindow）

## 目標

把「輸入框對話」正式納入 Context 系統：

- 每個 session_id 可回放 messages
- 窗口截斷一致且可配置

## 工作項

- **G3.1 session_id 規範**
  - 建議：前端生成 UUID，後端兜底生成

- **G3.2 記錄與讀取**
  - 使用既有 `genai/workflows/context/recorder.py` / `manager.py`

- **G3.3 ContextWindow 策略**
  - max_tokens / max_messages
  - FIFO +（可選）摘要

- **G3.4 與 MoE Chat 整合**
  - 進入 MoE 前，先組裝 messages（含 system + windowed history）

## 驗收

- session 對話可持續累積
- 窗口截斷後仍可正常回覆
