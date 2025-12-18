<!--
代碼功能說明: GenAI 先期實作主計劃（MoE Auto / 收藏模型 / 上下文與記憶）
創建日期: 2025-12-13 13:55 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-13 21:20:53 (UTC+8)
-->

# GenAI 先期實作主計劃（MVP → 可迭代）

## 0. 目的與範圍

### 0.1 目的
從前端「輸入框」開始，完成一條可運行的 GenAI 產品鏈路：

- **模型調用**：支援 **Auto（MoE）** 與 **我的收藏模型**（先期必做）
- **上下文/記憶**：支援短期上下文（Session）與最小可用的長期記憶（AAM/RAG）
- **代理調用**：Auto 或指定 Agent（**放到下一迭代**，本計劃先預留接口）

### 0.2 依據文件（本計劃基線）
- `docs/architecture/genai-pipeline-overview.md`
- `docs/architecture/llm-routing-architecture.md`
- `docs/文件上傳向量圖譜/文件操作.md`（觀測/狀態/任務隊列一致性）
- 既有 WBS 參考：
  - `docs/plans/phase4/wbs-4.3-context-management.md`
  - `docs/plans/phase4/wbs-4.4-aam-integration.md`
  - `docs/plans/phase5/wbs-5.1-LLM-Router實現計劃.md`

> 備註：你提到的 `@AI-Box/AAM/...` 文檔目前不在 repo 內；本計劃改以 **現有 AAM 模組與既有 phase4 WBS** 作為落地依據。

---

## 1. 現況盤點（關鍵差距）

### 1.1 MoE 已存在但未進入「主要對話入口」
- `llm/moe/moe_manager.py` 提供 `chat()` / `generate()`，**Auto 需依賴 task_classification**。
- `api/routers/llm.py` 目前 `/llm/chat` 走 **OllamaClient**，MoE 主要用於健康檢查與 stats。

**差距**：前端「輸入框」的核心聊天請求目前不會走 MoE，因此無法實現 Auto。

### 1.2 收藏模型（User Preference）尚未定義資料模型與 API
- 前端需要「Auto」+「收藏模型」選單。
- 後端需要可查詢/更新收藏模型（至少 user-level）。

### 1.3 上下文與記憶：已有基礎模組，但需要對齊「產品入口」
- Context：`genai/workflows/context/*` 已具備 recorder/window/persistence
- AAM：`agents/infra/memory/aam/*`、`genai/workflows/rag/*` 已存在

**差距**：尚未把「前端輸入框的對話」系統化接上：
- Session ID / Task ID 的規範
- 記憶檢索→注入 prompt 的標準接口
- 觀測性（記憶命中/路由決策）

### 1.4 你提出的「前端可選模型 / Auto + 參數化策略」：**已部分考慮，但本迭代尚未完全落地**

**已具備（現況）**
- 前端已存在模型下拉：`ai-bot/src/components/ChatInput.tsx` 有 `Auto` 與多模型列表（含 Ollama/ChatGPT/Gemini/Qwen/Grok）。
- 後端已具備 MoE 統一入口：`llm/moe/moe_manager.py` 支援 `chat()/generate()`，可接 `task_classification` 做 Auto routing。
- 專案已可透過 JSON 設定檔配置（未來可擴展為你說的「系統參數 json」）：`config/config.json`（由 `system/infra/config/config.py` 讀取）。

**尚未落地（本迭代缺口）**
- 前端選到的 `modelId` 目前 **沒有被寫回 task 的 executionConfig**，也 **沒有在送出訊息時傳給後端**（`ai-bot/src/components/ChatArea.tsx` 的 `onMessageSend` 目前仍是 stub）。
- 後端尚未提供「產品級 Chat API」來接收 `model_selector`（Auto/指定/收藏）並串進 MoE + Context/Memory。

> **標註**：此項目將在 **G1（前端串接）+ G2（MoE Chat 主入口）** 落地；目前屬於「規劃已納入、代碼基礎存在、但尚未接上主流程」。

### 1.5 你提出的「Agent Orchestration 依任務分析決定不同模型 + 指揮不同任務型 Agent」：**已納入方向，但本迭代不做（下一迭代）**

**已具備（現況）**
- 任務分析可產出：工作流類型與 LLM 路由建議（provider/model）：`agents/task_analyzer/analyzer.py` + `agents/task_analyzer/llm_router.py`。
- 代理平台具備：Agent Registry / Orchestrator / MCP 調用骨架：`agents/services/orchestrator/orchestrator.py`、`agents/services/registry/task_executor.py`。
- Hybrid 工作流可根據 context 做模式切換（但不含 per-agent model policy）：`agents/workflows/hybrid_orchestrator.py`。

**尚未落地（本迭代缺口）**
- 尚未建立「任務型 Agent（Security/Status/Report/WebCrawler…）」的標準介面與能力清單，也尚未做到 **每個子任務/每個 Agent 綁定不同模型策略**（例如 Security 用強模型、爬蟲用便宜模型、報表用長上下文模型）。

> **標註**：此項目對應 **G7（下一迭代）**，本迭代先把 MoE/Context/Memory 的產品入口打通，避免同時引入代理編排複雜度。

---

## 2. 里程碑與交付物

### 2.1 MVP 里程碑（建議 2 週節奏，可依人力調整）
- **M0（盤點對齊）**：接口/資料結構/追蹤點對齊完成
- **M1（模型入口）**：前端輸入框 → 後端 Chat API（支援 Auto + 收藏）可跑通
- **M2（短期上下文）**：Session 記錄/窗口截斷/可回放
- **M3（長期記憶 MVP）**：AAM 最小可用：檢索→注入→回覆（含觀測）
- **M4（可觀測/可評測）**：路由、成本、延遲、命中率指標可追蹤

### 2.2 交付物清單
- **主入口 API**：一套面向前端輸入框的 Chat API（建議新增專用 router，如 `/api/v1/chat`）
- **模型選擇**：Auto（MoE）與收藏模型（Preference）
- **上下文**：Session/ContextWindow + 追蹤
- **長期記憶**：AAM Retrieval + 注入策略（MVP）
- **指標**：routing_decision / memory_hit / token_cost / latency

---

## 3. 進度實施管控表（主控表）

> 說明：此表做為本主計劃的「單一真實來源（SSOT）」；每次迭代結束更新狀態與日期。

| WBS | 名稱 | 估時 | 依賴 | 狀態 | 進度 | 開始 | 完成 | 負責 |
|---|---|---:|---|---|---:|---|---|---|
| G0 | 基礎盤點與介面對齊 | 1.0w | - | ✅ | 100% | 2025-12-13 17:28:02 (UTC+8) | 2025-12-13 17:42:45 (UTC+8) | Daniel |
| G1 | 前端輸入框：Auto/收藏模型選擇 | 0.5w | G0 | ✅ | 100% | 2025-12-13 17:28:02 (UTC+8) | 2025-12-13 17:42:45 (UTC+8) | Daniel |
| G2 | MoE Auto 路由接入（Chat 主入口） | 0.5w | G0 | ✅ | 100% | 2025-12-13 17:28:02 (UTC+8) | 2025-12-13 17:42:45 (UTC+8) | Daniel |
| G3 | 短期上下文（Session/Window/Recorder） | 0.5w | G1,G2 | ✅ | 100% | 2025-12-13 19:46:41 (UTC+8) | 2025-12-13 20:06:02 (UTC+8) | Daniel |
| G4 | 長期記憶 MVP（AAM/RAG：檢索→注入） | 1.0w | G3 | ✅ | 100% | 2025-12-13 19:46:41 (UTC+8) | 2025-12-13 20:06:02 (UTC+8) | Daniel |
| G5 | 觀測性與評測（路由/命中率/成本） | 0.5w | G2,G4 | ✅ | 100% | 2025-12-13 20:15:11 (UTC+8) | 2025-12-13 21:00:38 (UTC+8) | Daniel |
| G6 | 安全與權限（模型資源/資料同意/隔離） | 0.5w | G1,G2,G3 | ✅ | 100% | 2025-12-13 21:09:37 (UTC+8) | 2025-12-13 21:20:53 (UTC+8) | Daniel |
| G7 | 代理調用（下一迭代：Auto/指定 Agent） | 1.0w | M1-M3 | 📌 | 0% | - | - | Daniel |

狀態圖例：⏳ 進行中 / ⏸️ 待開始 / ✅ 完成 / 📌 下一迭代

---

## 4. WBS 分解文件（本主計劃索引）

- `WBS/WBS-G0-基礎盤點與介面對齊.md`
- `WBS/WBS-G1-前端輸入框與模型選擇（Auto-收藏）.md`
- `WBS/WBS-G2-MoE-Auto-路由接入與偏好策略.md`
- `WBS/WBS-G3-短期上下文（Session-ContextWindow）.md`
- `WBS/WBS-G4-長期記憶MVP（AAM-RAG）.md`
- `WBS/WBS-G5-觀測性與評測（Routing-Memory）.md`
- `WBS/WBS-G6-安全與權限（Consent-RBAC）.md`
- `WBS/WBS-G7-代理調用（下一迭代）.md`

---

## 5. 先期架構決策（ADR 摘要）

### 5.1 技術選型決策（定案）

**結論**：採用「混用」作為架構，但「收斂到兩個主引擎」作為落地策略：

- **LangGraph（LangChain 生態）**：作為 **預設主引擎**（穩定、可觀測、可回放/checkpoint）
- **AutoGen**：作為 **複雜任務的規劃/多代理協作引擎**（長程規劃、動態多輪）
- **CrewAI**：保留為 **可選插件**（特定模板化協作流程再啟用），避免三套同時深度綁死

此決策與現有代碼一致：
- `agents/task_analyzer/workflow_selector.py` 已具備 `LANGCHAIN / AUTOGEN / CREWAI / HYBRID` 選擇
- `agents/workflows/hybrid_orchestrator.py` 已實作 **AutoGen ↔ LangGraph** 狀態同步與切換

### 5.2 混用邊界（必須遵守）

為了確保「多模型、多代理」可擴展且不被框架綁死，本系統定義以下邊界：

- **LLM 路由（MoE）獨立於工作流引擎**
  - Auto / 收藏模型 → 最終都要走 `LLMMoEManager`（或其統一封裝）
  - 工作流引擎只產生「需要呼叫 LLM 的請求」，不直接綁 provider

- **Context / Memory 獨立於工作流引擎**
  - Context（短期）：session history + window（Redis / ContextWindow）
  - Memory（長期）：RAG/Graph（ChromaDB / ArangoDB）
  - 引擎只透過統一接口取得「可注入的 context/memory blocks」

- **工具調用（Tools/MCP）獨立於工作流引擎**
  - 工具 registry / 權限 / audit 由平台統一層處理

### 5.3 官方執行路徑（面向前端輸入框）

- **預設路徑（大多數請求）**：
  - 前端輸入框 → `Chat Product API` → **LangGraph**（主流程）

- **升級路徑（複雜任務）**：
  - `TaskAnalyzer` 判定複雜度 ≥ 閾值（例如 70）或步驟數 > 10 → `HYBRID`
  - **Hybrid（primary: AutoGen, fallback: LangGraph）** 或依策略切換

- **模型選擇（與引擎無關）**：
  - **Auto**：MoE + task_classification（provider/model 由策略決定）
  - **收藏模型**：manual override（固定 provider/model），可覆蓋 Auto

### 5.4 何時用哪個引擎（快速準則）

| 場景 | 建議引擎 | 理由 | 典型例子 |
|---|---|---|---|
| 單輪/少輪、標準工具流程、需要可觀測/可回放 | **LangGraph** | state machine + checkpoint 友好 | RAG 問答、文件摘要、資料抽取流程 |
| 長程規劃、多代理協作、需要動態改 plan | **AutoGen** | planner/coordination 強 | 複雜任務分解、跨工具多步協作 |
| 介於兩者、或有錯誤/成本風險需要切換 | **Hybrid** | 兼顧規劃與穩定性 | 高複雜度任務，先規劃再落地執行 |
| 明確角色模板、固定協作劇本 | CrewAI（可選） | 模板化管理 | 固定角色協作（例如 PM/Dev/QA） |

### 5.5 統一治理（避免框架碎片化）

- **一個產品入口**：前端輸入框只打「產品級 Chat API」，不直接選 LangGraph/AutoGen
- **一個 MoE 層**：所有引擎的 LLM 呼叫統一走 MoE（Auto/收藏都可）
- **一套記憶策略**：ContextWindow + Memory retrieval 注入策略一致
- **一套觀測字段**：routing_decision / memory_hit / token_cost / latency


## 6. 風險與對策（先期）

| 風險 | 影響 | 對策 |
|---|---|---|
| Auto 需要 task_classification，但入口未提供 | 高 | 在 Chat 入口內部自動調用 task_analyzer（或提供 fallback 預設分類） |
| 收藏模型跨 provider（Ollama/Gemini/ChatGPT）參數不一致 | 中 | 統一「模型選項 schema」，按 provider 做 adapter |
| 記憶檢索注入造成 prompt 膨脹 | 中 | ContextWindow + memory top-k + 摘要策略 |
| 觀測不足導致無法迭代 | 高 | routing_decision + memory_hit + cost/latency 先期就做 |

---

**文檔版本**: 0.3
