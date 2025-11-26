<!--
代碼功能說明: WBS 3.1 LangChain/Graph 整合子計劃
創建日期: 2025-11-26 19:58 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-26 19:58 (UTC+8)
-->

# WBS 3.1 LangChain/Graph 整合子計劃

## 1. 背景與目標
- 依據 `plans2/階段三-工作流引擎計劃.md`，LangChain/Graph 為 Task Analyzer 選出的第一層工作流骨幹，必須提供高可靠度的 FSM、條件分支以及任務可觀測性。
- 完成後需支撐 PROJECT_CONTROL_TABLE 中 M3 里程碑的 LangChain 相關 KPI（完成度 100%，可透過功能測試驗收）。
- 與現有 Task Analyzer、Agent Orchestrator、Memory/Tool/Prompt Managers 深度整合，確保 Agent AI Box 架構圖中「Task Analyzer 工作流引擎」區塊可以落地。

## 2. 工作範圍
- 建立 LangChain Pipeline/LCEL 組件並封裝為 Task Analyzer 可直接調用的 workflow factory。
- 實作 LangGraph 狀態機（含節點、邊、全域狀態序列化）並將狀態資料寫入 Context Recorder。
- 實現分叉/條件判斷模組，支援複雜路由策略及可觀測事件。
- 建置 workflow telemetry：行程事件、節點耗時、錯誤堆疊，串接既有監控通道。

## 3. 任務拆解
| 任務 ID | 名稱 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|------|--------|------|------|
| T3.1.1 | LangChain 核心整合 | 封裝 Pipeline、LCEL、RunnableConfig，提供標準介面 | AI-1 | 2 天 | 階段二 Task Analyzer API |
| T3.1.2 | LangGraph 狀態機 | 定義 Graph schema、節點/邊、序列化策略 | AI-1 | 2 天 | T3.1.1 |
| T3.1.3 | 分叉判斷邏輯 | 實作條件路由、閾值/權重判斷與 fallback | AI-1 | 1.5 天 | T3.1.2 |
| T3.1.4 | 狀態可觀測性 | 事件匯流排、metrics/logging 與可視化鉤子 | AI-1 | 1.5 天 | T3.1.2 |

## 4. 技術方案與整合點
- **Workflow Factory**：於 `agents/workflows/langchain_graph_factory.py`（新檔）輸出標準 `build_workflow(request_ctx)` 介面，供 Task Analyzer 依任務複雜度調用。
- **狀態儲存**：透過 LangGraph checkpoint handler 將 state 持久化至 Redis（短期）與 Context Recorder（長期），並與 AAM 模組的 STM/LTM 結構保持一致。
- **可觀測性**：導出節點事件至 `services/api/telemetry`，並提供 Prometheus 指標（節點耗時、重試次數、分支命中率）。
- **配置管理**：新增 `config/config.json` → `workflows.langchain_graph` 區塊（非敏感）與 `.env` 中的敏感連線字串（遵守配置規範）。

## 5. 里程碑與時間表（對應工作日 D51-D57 / 2026-01-21 ~ 2026-01-29）
- D51-D52：完成 T3.1.1，提交 Workflow Factory PR 與單元測試。
- D53-D54：實作 T3.1.2，落實狀態序列化、checkpoint 測試。
- D55：完成 T3.1.3，與 Task Analyzer 工作流選擇器進行 E2E 測試。
- D56：完成 T3.1.4，串接 Observability Stack（metrics/logs/traces）。
- D57：綜合驗收與與 WBS 3.2/3.3 介面對齊（確保後續混合模式可共用狀態）。

## 6. 交付物
- `agents/workflows/langchain_graph/` 目錄（Factory、Graph 定義、路由模組、測試）。
- 配置文件更新：`config/config.example.json`、`docs/plans/phase3/wbs-3.1` 所屬架構說明。
- 測試與報告：單元測試、E2E 測試腳本、可觀測性儀表板說明。

## 7. 風險與緩解
| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| LangGraph 與現有記憶體管理不一致 | 狀態遺失或重放錯誤 | 先以 staging Redis 測試 checkpoint，並撰寫回放腳本 |
| 觀測資料量過大 | 監控成本升高 | 透過取樣率及事件壓縮策略（只記錄節點進出與錯誤） |
| Workflow Factory 與其他工作流 API 不一致 | Task Analyzer 無法切換 | 撰寫 `WorkflowContract` 介面測試，確保輸入輸出結構統一 |

## 8. 驗收標準
- Task Analyzer 在複雜度 30-50 任務時可自動選擇 LangChain/Graph 流程並成功執行。
- LangGraph 狀態可於 Redis/Context Recorder 中重放並恢復。
- Observability dashboard 可顯示節點耗時、分支命中、錯誤率且指標經壓力測試驗證。

## 9. 更新紀錄
| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-26 | 初版子計劃建立 | Daniel Chung |
