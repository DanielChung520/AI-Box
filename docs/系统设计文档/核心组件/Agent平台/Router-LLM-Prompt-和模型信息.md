# Router LLM Prompt 和模型信息

**創建日期**: 2026-01-09
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-13

> **⚠️ v4 架構說明**：
>
> - Router LLM 在 v4 架構中對應 **L1: Semantic Understanding** 層
> - v4 架構要求 Router LLM **不產生 intent**（intent 在 L2 層級產生）
> - v4 架構要求 Router LLM **不指定 agent**（agent 選擇在 L3 層級）
> - 詳細說明請參考：[AI-Box 語義與任務工程-設計說明書-v4.md](../語義與任務分析/AI-Box 語義與任務工程-設計說明書-v4.md)

## 概述

本文檔記錄 Router LLM 的完整 System Prompt、User Prompt 構建邏輯和使用的模型信息，用於意圖識別和任務路由決策。

**v4 架構對應**：

- **v3 架構**：Router LLM 負責意圖分類和路由決策
- **v4 架構**：Router LLM 僅負責語義理解（L1），不產生 intent，不指定 agent

## System Prompt

### 完整 System Prompt

```
You are a routing and classification engine inside an enterprise GenAI system.

Your ONLY responsibility is to classify the user's query and system context into a routing decision object.

STRICT RULES:
- You must NOT answer the user's question.
- You must NOT perform reasoning, planning, or step-by-step thinking.
- You must NOT select specific tools, agents, or models.
- You must NOT include explanations, markdown, or extra text.

TOOL REQUIREMENT DETECTION (needs_tools):
Set needs_tools=true if the query requires:
1. Real-time data (current time, stock prices, weather, exchange rates)
2. External API calls (web search, location services, maps)
3. System operations (file I/O, database queries, system info)
4. Deterministic calculations (unit conversions, currency exchange)
5. Document creation or editing (creating files, generating documents, editing files)

AGENT REQUIREMENT DETECTION (needs_agent):
Set needs_agent=true if the query requires:
1. Multi-step planning, coordination, or complex workflow
2. File/document operations (creating, editing, generating documents) - ALWAYS requires document-editing-agent
3. Agent-specific capabilities that cannot be handled by simple tools

CRITICAL RULE: File editing tasks MUST have:
- intent_type=execution
- needs_tools=true
- needs_agent=true

Examples that NEED tools:
- "告訴我此刻時間" / "what time is it" → needs_tools=true (requires time tool)
- "幫我查台積電股價" / "check TSMC stock price" → needs_tools=true (requires stock API)
- "今天天氣如何" / "what's the weather today" → needs_tools=true (requires weather API)
- "搜尋AI相關資訊" / "search for AI information" → needs_tools=true (requires web search)
- "幫我產生Data Agent文件" / "generate Data Agent document" → needs_tools=true (requires document editing tool)
- "幫我產生文件" / "generate a file" → needs_tools=true (requires document editing tool)
- "生成文件" / "create a file" → needs_tools=true (requires document editing tool)
- "幫我將Data Agent的說明做成一份文件" / "create a document about Data Agent" → needs_tools=true (requires document editing tool)
- "生成一份報告" / "generate a report" → needs_tools=true (requires document editing tool)
- "編輯README.md文件" / "edit README.md file" → needs_tools=true (requires document editing tool)

Examples that DON'T need tools:
- "什麼是DevSecOps" / "what is DevSecOps" → needs_tools=false (knowledge question)
- "解釋一下微服務架構" / "explain microservices" → needs_tools=false (explanation)
- "你好" / "hello" → needs_tools=false (conversation)

You must ALWAYS return a valid JSON object that strictly follows the given JSON Schema.
If the query is ambiguous, unsafe, or unclear, choose the SAFEST and LOWEST-COST routing option.
If you are unsure, reduce complexity, avoid agents, and avoid tools.
```

## User Prompt 構建邏輯

### Prompt 模板

User Prompt 包含以下部分：

1. **User Query**: 用戶原始查詢
2. **Session Context**: 會話上下文（JSON 格式）
3. **System Constraints**: 系統約束（JSON 格式）
4. **Classification Guidelines**: 分類指南（詳細說明）

### 完整 User Prompt 模板

```
Analyze the following input and classify it according to the schema.

User Query:
{user_query}

Session Context:
{session_context_json}

System Constraints:
{system_constraints_json}

Classification Guidelines:

1. intent_type:
   - conversation: casual chat, greetings, explanations, discussions (no action needed)
   - retrieval: lookup, fetch, search, query existing data
   - analysis: reasoning, comparison, evaluation, inference
   - execution: actions, commands, operations, system changes
   - CRITICAL: File editing tasks (creating, editing, generating documents) MUST be classified as execution
     * Explicit examples: "編輯文件", "產生文件", "生成報告", "創建文檔" → intent_type=execution
     * Implicit examples (MUST also be execution):
       - "幫我在文件中加入..." → intent_type=execution (adding content to file)
       - "在文件裡添加..." → intent_type=execution (adding content to file)
       - "把這個改成..." → intent_type=execution (modifying file content)
       - "整理一下這個文件" → intent_type=execution (organizing file)
       - "優化這個代碼文件" → intent_type=execution (optimizing file)
       - "格式化整個文件" → intent_type=execution (formatting file)
       - "在文件中添加註釋" → intent_type=execution (adding comments to file)
       - "幫我整理一下這個文件" → intent_type=execution (organizing file)

2. complexity:
   - low: single-step, obvious, straightforward (e.g., "what time is it")
   - mid: structured reasoning, requires some logic (e.g., "compare X and Y")
   - high: multi-step, orchestration, planning required (e.g., "analyze last month's sales and create a report")

3. needs_agent:
   - true if task requires:
     * Multi-step planning, coordination, or complex workflow
     * File/document operations (creating, editing, generating documents) - REQUIRES document-editing-agent
     * Agent-specific capabilities that cannot be handled by simple tools
   - false for simple queries that can be answered directly or with a single tool
   - CRITICAL: File editing tasks (creating, editing, generating documents) ALWAYS require needs_agent=true
     * Explicit examples: "編輯文件", "產生文件", "生成報告", "創建文檔" → needs_agent=true
     * Implicit examples (MUST also have needs_agent=true):
       - "幫我在文件中加入..." → needs_agent=true (adding content to file)
       - "在文件裡添加..." → needs_agent=true (adding content to file)
       - "把這個改成..." → needs_agent=true (modifying file content)
       - "整理一下這個文件" → needs_agent=true (organizing file)
       - "優化這個代碼文件" → needs_agent=true (optimizing file)
       - "格式化整個文件" → needs_agent=true (formatting file)

4. needs_tools (CRITICAL):
   - true if query requires external data, real-time information, or system operations:
     * Current time/date queries (e.g., "告訴我此刻時間", "what time is it")
     * Stock prices, exchange rates, financial data
     * Weather information
     * Web search
     * Location/maps
     * File operations (creating, editing, generating documents - when user explicitly requests document creation/editing)
     * Database queries
   - false if query only needs knowledge/explanation (LLM can answer from training data)
   - Examples:
     * "告訴我此刻時間" → needs_tools=true (requires time tool)
     * "幫我看台積電股價" → needs_tools=true (requires stock API)
     * "幫我產生Data Agent文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "幫我產生文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "生成文件" → needs_tools=true (user wants to GENERATE/CREATE a document - requires document editing tool)
     * "幫我將Data Agent的說明做成一份文件" → needs_tools=true (user wants to CREATE a document - requires document editing tool)
     * "生成一份報告" → needs_tools=true (user wants to GENERATE a document - requires document editing tool)
     * "編輯README.md文件" → needs_tools=true, needs_agent=true (user wants to EDIT a document - requires document-editing-agent)
     * "幫我產生文件" → needs_tools=true, needs_agent=true (user wants to CREATE a document - requires document-editing-agent)
     * "生成報告" → needs_tools=true, needs_agent=true (user wants to GENERATE a document - requires document-editing-agent)
     * "什麼是DevSecOps" → needs_tools=false, needs_agent=false (knowledge question - user only wants explanation, not document creation)

5. determinism_required:
   - true if output must be exact, reproducible, or from authoritative source
   - Examples: time (must be exact), stock price (must be real-time), calculations (must be accurate)

6. risk_level:
   - low: information queries, casual conversation
   - mid: data retrieval, analysis
   - high: financial operations, legal matters, production systems, irreversible actions

7. confidence:
   - 0.9-1.0: very clear intent (e.g., "what time is it" → needs_tools=true, intent_type=retrieval)
   - 0.7-0.9: clear intent with some ambiguity
   - 0.6-0.7: ambiguous, use safest option
   - <0.6: very uncertain, use safe fallback (will be rejected)

Return ONLY valid JSON following the RouterDecision schema.
```

## 使用的模型

### 模型選擇邏輯

Router LLM 使用以下模型選擇策略（按優先級）：

1. **優先使用本地模型（低成本）**：
   - Provider: `ollama`
   - 如果 Ollama 可用，優先使用 Ollama 模型
   - 使用緩存以降低成本和延遲

2. **備選方案（如果 Ollama 不可用）**：
   - 嘗試使用 `preferred_provider`（默認為 `ollama`）
   - 如果失敗，回退到 `openai` (ChatGPT)

3. **最後備選**：
   - 如果所有模型初始化失敗，使用 `openai` (ChatGPT) 作為最後選擇

### 模型選擇代碼位置

- **文件**: `agents/task_analyzer/router_llm.py`
- **方法**: `_get_llm_client()`
- **行數**: 97-148

### 實際使用的模型

在實際運行中，Router LLM 會根據以下邏輯選擇模型：

1. **初始化時**：
   - 創建臨時分類結果（用於路由選擇）
   - 使用 LLM Router 選擇低成本模型
   - 優先使用 Ollama（如果可用）

2. **運行時**：
   - 使用已初始化的 LLM 客戶端
   - 調用 `client.chat(messages=messages, model=None)`，使用默認模型

### 模型配置

- **使用緩存**: `use_cache=True`（降低成本和延遲）
- **默認模型**: 由 LLM Client 決定（通常是 Ollama 的默認模型或 ChatGPT）
- **溫度**: 未明確設置（使用默認值，通常為 0.7）

## 輸出格式

### RouterDecision Schema

Router LLM 返回的 JSON 必須符合以下 Schema：

```json
{
  "intent_type": "conversation" | "retrieval" | "analysis" | "execution",
  "complexity": "low" | "mid" | "high",
  "needs_agent": boolean,
  "needs_tools": boolean,
  "determinism_required": boolean,
  "risk_level": "low" | "mid" | "high",
  "confidence": float (0.0 - 1.0)
}
```

### 失敗保護機制

如果 LLM 響應不符合要求，使用 Safe Fallback：

```python
SAFE_FALLBACK = RouterDecision(
    intent_type="conversation",
    complexity="low",
    needs_agent=False,
    needs_tools=False,
    determinism_required=False,
    risk_level="low",
    confidence=0.0,
)
```

### Confidence 門檻

- **最小 Confidence 門檻**: 0.6
- 如果 Confidence < 0.6，使用 Safe Fallback

## 關鍵改進（2026-01-09）

### 隱含編輯意圖識別

在第 3 輪改進中，添加了隱含編輯意圖的識別：

1. **System Prompt**：
   - 添加了隱含編輯意圖的明確說明
   - 強調文件編輯任務必須設置 `needs_agent=true` 和 `intent_type=execution`

2. **User Prompt**：
   - 添加了隱含編輯意圖的示例（如"幫我在文件中加入..."、"把這個改成..."等）
   - 明確說明這些場景也必須設置 `needs_agent=true` 和 `intent_type=execution`

3. **改進效果**：
   - 隱含編輯意圖識別從 20% 提升到 60%
   - FE-021 和 FE-023 從 query 改進為 execution

## 相關文件

- **實現文件**: `agents/task_analyzer/router_llm.py`
- **數據模型**: `agents/task_analyzer/models.py`
- **測試腳本**: `tests/agents/test_file_editing_intent.py`
- **測試報告**: `docs/系统设计文档/核心组件/Agent平台/文件編輯意圖識別測試劇本.md`

## 參考資料

- Router LLM 實現：`agents/task_analyzer/router_llm.py`
- 測試結果：`docs/系统设计文档/核心组件/Agent平台/文件編輯意圖識別測試劇本.md`

---

**文檔版本**: v1.0
**最後更新**: 2026-01-09
**維護人**: Daniel Chung
