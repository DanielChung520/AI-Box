<!--
代碼功能說明: WBS-G2 MoE Auto 路由接入與偏好策略
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G2：MoE Auto 路由接入與偏好策略

## 目標
讓「Auto」真的走 MoE：
- 入口 Chat API 內部完成 task_analyzer → moe_manager.chat
- 收藏模型可覆蓋 provider/model（manual）

## 工作項
- **G2.1 新增/調整 Chat 產品入口**
  - 建議新增 `api/routers/chat.py`（或在既有路由中新增 `/chat` 產品端點）

- **G2.2 Task Classification**
  - 調用 task_analyzer（內部服務或既有 endpoint）
  - 產出 `TaskClassificationResult` 給 MoE

- **G2.3 MoE 路由結果回傳**
  - response 補：provider、strategy、latency、fallback（若發生）

- **G2.4 收藏模型覆蓋規則**
  - 若 user 選了收藏模型：provider/model 強制指定
  - 若 Auto：只允許 policy 範圍內 provider（可加入 RBAC/consent gate）

## 驗收
- Auto 模式請求可穩定走 MoE
- 失敗能 failover（若 enable_failover）
- 收藏模型能覆蓋 Auto
