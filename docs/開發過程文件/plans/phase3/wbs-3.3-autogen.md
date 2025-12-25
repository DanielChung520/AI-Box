<!--
代碼功能說明: WBS 3.3 AutoGen 整合子計劃
創建日期: 2025-11-26 19:58 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-26 19:58 (UTC+8)
-->

# WBS 3.3 AutoGen 整合子計劃

## 1. 背景與目標

- AutoGen 提供 Long-horizon 自動規劃與多步驟任務處理，是階段三支援 60-80 複雜度任務的關鍵模組。
- 需根據 PROJECT_CONTROL_TABLE 於 6 個工作日內交付，確保 Task Analyzer 可根據複雜度和步數需求選擇 AutoGen。
- 需與 LangGraph 狀態、CrewAI 多代理結果互通，並支援混合模式（WBS 3.4）後續組合。

## 2. 工作範圍

- 基礎設置：環境、依賴安裝、LLM/Tool 路由、配置模板。
- AutoGen Agent：定義規劃 Agent、執行 Agent、評估 Agent，支援多 Agent 協作。
- Execution Planning：多步驟計畫生成、回饋修正、失敗重試策略。
- Long-horizon 任務處理：狀態持久化、checkpoint、長程記憶與成本控制。

## 3. 任務拆解

| 任務 ID | 名稱 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|------|--------|------|------|
| T3.3.1 | AutoGen 基礎設置 | 安裝、設定檔、與 LLM Router/Credential 對接 | AI-2 | 0.5 天 | WBS 3.1 Workflow Factory |
| T3.3.2 | AutoGen Agent 實現 | 建立多 Agent 角色、會話管理、工具接口 | AI-2 | 2 天 | T3.3.1 |
| T3.3.3 | Execution Planning | 規劃/重規劃、計畫驗證與成本估算 | AI-2 | 2 天 | T3.3.2 |
| T3.3.4 | Long-horizon 任務處理 | 狀態管理、持久化、長程記憶及失敗恢復 | AI-2 | 1.5 天 | T3.3.3 |

## 4. 技術方案與整合點

- **模組架構**：建立 `agents/autogen/` 目錄，含 `config.py`, `agent_roles.py`, `planner.py`, `long_horizon.py`, `tests/`。
- **計畫記錄**：Execution Planning 結果寫入 Context Recorder，並將 cost/tokens 紀錄至 `services/api/telemetry`.
- **狀態同步**：與 LangGraph/Task Analyzer 共用 `WorkflowContract`，允許計畫節點轉換成狀態機節點；必要時輸出 partial plan 供 CrewAI 參照。
- **資源控制**：配置 `auto_retry`, `max_rounds`, `budget_tokens`，確保 Steps > 5 之任務仍可控。

## 5. 里程碑與時間表（對應工作日 D58-D63 / 2026-01-30 ~ 2026-02-06，可與 WBS 3.2 並行）

- D58：完成 T3.3.1，交付設定檔與驗證腳本。
- D59-D60：完成 T3.3.2，提供多 Agent 協作示例與單元測試。
- D61-D62：完成 T3.3.3，產出計畫生成/驗證 API 與成本預估報告。
- D63：完成 T3.3.4，長程任務可支援暫停/恢復並寫入記憶系統。

## 6. 交付物

- `agents/autogen/` 模組 + 測試。
- Execution Planning 報告範本與自動化測試腳本。
- Context Recorder schema 更新、長程狀態 dump/replay 文檔。

## 7. 風險與緩解

| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| AutoGen 版本變動 | API 不相容 | 鎖定版本並建立 smoke test，若失敗切回上一版本 |
| 長程任務佔用資源過久 | CI/CD pipeline 受阻 | 加入最大迭代數、空閒監控與自動暫停機制 |
| 與 LangGraph 狀態不同步 | 混合模式不可用 | 於 Execution Planning 階段就輸出狀態草稿，並撰寫契約測試 |

## 8. 驗收標準

- 複雜度 60-80 的樣板任務可由 AutoGen 自動規劃並成功執行。
- Execution Planning 可輸出可讀計畫摘要、成本預估、以及可重播的狀態檔。
- Long-horizon 任務可暫停/恢復並保持一致性，且失敗後可透過重試成功。

## 9. 更新紀錄

| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-26 | 初版子計劃建立 | Daniel Chung |
