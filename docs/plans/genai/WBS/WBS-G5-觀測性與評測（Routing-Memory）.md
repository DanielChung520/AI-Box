<!--
代碼功能說明: WBS-G5 觀測性與評測（Routing/Memory）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G5：觀測性與評測（Routing / Memory）

## 目標

讓 MoE 與 Memory 可以快速迭代：

- 每次請求都能看見：路由決策、fallback、延遲
- Memory 命中可追蹤

## 工作項

- 統一 log fields（request_id/session_id/task_id/provider/model/strategy）
- 指標：latency / token / cost（能取到多少算多少）
- Memory 指標：hit/miss、top-k、來源（vector/graph）
- 形成最小評測腳本或測試案例（回歸用）

## 驗收

- 透過 log 能完整追一條請求
- 有可回歸的測試用例或腳本
