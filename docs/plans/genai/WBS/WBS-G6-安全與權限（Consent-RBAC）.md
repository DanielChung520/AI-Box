<!--
代碼功能說明: WBS-G6 安全與權限（Consent/RBAC）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 13:55 (UTC+8)
-->

# WBS-G6：安全與權限（Consent / RBAC）

## 目標

確保「Auto/收藏模型」不會繞過既有治理與權限：

- provider/model 使用權限
- 資料同意（data consent）
- 租戶/使用者隔離

## 工作項

- 收藏模型與 Auto 的 policy gate（允許清單）
- MoE client factory 的 resource control（agent_id/user_id 綁定策略）
- 記憶資料隔離（user_id/task_id）

## 驗收

- 未授權 provider/model 無法被呼叫
- 記憶不會跨 user 泄漏
