<!--
代碼功能說明: WBS 3.4 AutoGen + LangGraph 混合模式子計劃
創建日期: 2025-11-26 19:58 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-11-26 19:58 (UTC+8)
-->

# WBS 3.4 AutoGen + LangGraph 混合模式子計劃

## 1. 背景與目標
- 混合模式為階段三的收斂工作，將 AutoGen 的長程規劃能力與 LangGraph 的狀態可觀測性結合，支援 PROJECT_CONTROL_TABLE 中 ≥70 分超高複雜度任務。
- 需實作模式選擇邏輯與動態切換，確保 Task Analyzer 可根據複雜度、狀態需求、角色需求自動挑選單一/混合模式，並在執行期間隨時切換。
- 完成後直接影響 M3 里程碑「混合模式可用性 ≥95%」指標。

## 2. 工作範圍
- 建立混合模式核心：流程編排器、狀態/計畫同步器、錯誤恢復策略。
- 模式選擇邏輯：根據複雜度、步驟、角色、資料依賴、失敗歷史等指標判斷使用單一或混合模式。
- 模式切換機制：在執行期間可從 LangGraph 切換至 AutoGen（需規劃）或從 AutoGen 切換至 LangGraph（需可觀測與回放），確保狀態一致。

## 3. 任務拆解
| 任務 ID | 名稱 | 描述 | 負責人 | 工期 | 依賴 |
|---------|------|------|--------|------|------|
| T3.4.1 | 混合模式核心 | 建立 orchestrator、同步器與共享上下文格式 | AI-1 | 2 天 | WBS 3.1, WBS 3.3 |
| T3.4.2 | 模式選擇邏輯 | 設計決策樹/規則，串接複雜度分數與任務指標 | AI-1 | 1.5 天 | T3.4.1 |
| T3.4.3 | 模式切換機制 | 實作執行中切換、狀態遷移、回退策略 | AI-1 | 1.5 天 | T3.4.2 |

## 4. 技術方案與整合點
- **Hybrid Orchestrator**：新增 `agents/workflows/hybrid_orchestrator.py`，內含：
  - `PlanningSync`: 將 AutoGen 計畫節點對映為 LangGraph 狀態。
  - `StateSync`: 將 LangGraph 狀態輸出為 AutoGen 計畫上下文。
  - `SwitchController`: 定義切換條件與動作（pause/resume、state dump）。
- **Decision Engine**：擴充 Task Analyzer 輸出 `workflow_strategy`，包含 `mode=single|hybrid`、`primary=langgraph|autogen|crewai`、`fallback=[]`。
- **可觀測性**：為切換行為記錄事件（switch_reason、cost_delta、state_hash）並寫入 Telemetry，支撐模式成功率 KPI。

## 5. 里程碑與時間表（對應工作日 D66-D73 / 2026-02-09 ~ 2026-02-24）
- D66-D67：完成 T3.4.1，交付 Hybrid Orchestrator 原型與契約測試。
- D68-D69：完成 T3.4.2，Decision Engine 規則與 Task Analyzer 整合。
- D70-D72：完成 T3.4.3，切換機制（含回退、成本比較、觀測指標）。
- D73：混合模式全流程驗收（含 CrewAI/AutoGen/LangGraph 三者串聯）與 M3 里程碑驗收資料。

## 6. 交付物
- `agents/workflows/hybrid_orchestrator.py` 與測試。
- Task Analyzer 決策規則文件、模式切換流程圖、KPI 報表模板。
- Demo notebook/腳本：展示混合任務（AutoGen 規劃 → LangGraph 執行 → AutoGen 調整）的實際輸出。

## 7. 風險與緩解
| 風險 | 影響 | 緩解策略 |
|------|------|----------|
| 狀態與計畫資料結構不一致 | 切換失敗或資料遺失 | 制定統一 `HybridState` schema，並撰寫契約測試與序列化驗證 |
| 切換過於頻繁造成成本上升 | 觸發 KPI 失敗 | Decision Engine 加入冷卻時間與成本門檻，必要時鎖定模式 |
| 觀測指標不足以驗證 95% 成功率 | 無法驗收 | 列出完整事件欄位（start/stop/success）並同步至 Grafana Dashboard |

## 8. 驗收標準
- 在測試樣本中，AutoGen+LangGraph 混合任務成功率 ≥95%，且狀態可於任意切換點被回放。
- Task Analyzer 能輸出 `workflow_strategy` 並於執行期間根據條件觸發切換。
- Telemetry 報表可顯示切換原因、耗時、成功率，並與 PROJECT_CONTROL_TABLE 指標對齊。

## 9. 更新紀錄
| 日期 | 說明 | 更新人 |
|------|------|--------|
| 2025-11-26 | 初版子計劃建立 | Daniel Chung |
