<!--
代碼功能說明: WBS 3.2 CrewAI 整合子計劃
創建日期: 2025-11-26 19:58 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-26 19:58 (UTC+8)
-->

# WBS 3.2 CrewAI 整合子計劃

## 1. 背景與目標
- CrewAI 為階段三的多角色協作引擎，用於 PROJECT_CONTROL_TABLE 中 50-70 分複雜度任務，需覆蓋 Sequential、Hierarchical、Consensual 流程。
- 需與 AI-Box 架構中的 Agent Orchestrator、Task Analyzer、Memory/Tool Registry 無縫整合，確保多 Agent 任務能被調度、監控並回填結果。
- 目標是在 7.5 個工作日內交付完整的 Crew Manager、流程引擎、Agent 模板與 Task 管理系統。

## 2. 工作範圍
- 安裝與配置 CrewAI，封裝環境設定、模型路由與工具適配層。
- 實作 Crew Manager：隊伍定義、角色權限、資源配額、隊伍級別的觀測指標。
- 建立 Process Engine：實作 Sequential/Hierarchical/Consensual 三種流程模版與切換策略。
- 開發標準 Agent 模板 + 任務模型(Task definition, dispatch, feedback loop)。

## 3. 任務拆解
| 任務 ID | 名稱 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|------|--------|------|------|
| T3.2.1 | CrewAI 基礎設置 | 安裝套件、建立設定檔、串接 LLM Router | AI-1 | 0.5 天 | WBS 3.1 工作流接口 |
| T3.2.2 | Crew Manager 實現 | 隊伍/角色/資源分配模組與 API | AI-1 | 2 天 | T3.2.1 |
| T3.2.3 | Process Engine 實現 | 提供 3 種流程模板與切換邏輯 | AI-1 | 2 天 | T3.2.2 |
| T3.2.4 | Agent 模板開發 | 覆蓋規劃/研究/執行/評審等標準角色 | AI-1 | 1.5 天 | T3.2.2 |
| T3.2.5 | Task 管理系統 | 任務定義、排程、狀態跟蹤與審批 | AI-1 | 1.5 天 | T3.2.3, T3.2.4 |

## 4. 技術方案與整合點
- **模組結構**：於 `agents/crewai/` 新增 `manager.py`, `process_engine.py`, `agent_templates.py`, `task_registry.py`。
- **配置**：`config/config.json` 新增 `workflows.crewai` 區塊，含流程預設參數與資源上限；敏感 API key 仍置於 `.env`/Secret。
- **Orchestrator 對接**：Agent Orchestrator 透過 MCP 工具調用 CrewAI 任務；Task Analyzer 於複雜度 50-70 且需要多角色時選用 CrewAI。
- **資料回寫**：任務執行情況透過 Context Recorder 記錄，並同步到 PROJECT_CONTROL_TABLE 所需的進度欄位。

## 5. 里程碑與時間表（對應工作日 D58-D65 / 2026-01-30 ~ 2026-02-08）
- D58（0.5 日）：完成 T3.2.1，提交安裝腳本與設定檔。
- D58-D60：完成 T3.2.2，交付 Crew Manager API 與單元測試。
- D61-D62：完成 T3.2.3，三種流程模板可被調用並可在測試中切換。
- D63：完成 T3.2.4，提供至少 4 個核心 Agent 模板並與 Tool Registry 對接。
- D64-D65：完成 T3.2.5，輸出 Task 管理 API 與 E2E 測試報告。

## 6. 交付物
- `agents/crewai/` 目錄與對應測試。
- Workflow 設定文件、隊伍/流程樣板 YAML、Task 管理 API 規格。
- 集成測試腳本：CrewAI 任務全流程 + Task Analyzer 條件切換。

## 7. 風險與緩解
| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| CrewAI 與既有工具不兼容 | 無法呼叫內部工具 | 建立工具適配層 + 回退至 LangChain Workflow |
| 多角色協作造成 Token 成本暴增 | 成本失控 | 在 Process Engine 加入 Token Budget 守門與分支停損 |
| 流程狀態同步延遲 | Orchestrator 無法正確顯示狀況 | 透過事件匯流排 (Redis Stream) 實作即時狀態推送 |

## 8. 驗收標準
- Task Analyzer 在判斷需多角色時可切換到 CrewAI，整個任務全程成功完成。
- 三種流程模板可透過配置檔切換並通過集成測試。
- 各 Agent 模板均能調用 Tool Registry 工具並回寫結果，Task 管理系統可提供任務狀態查詢 API。

## 9. 更新紀錄
| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-26 | 初版子計劃建立 | Daniel Chung |
