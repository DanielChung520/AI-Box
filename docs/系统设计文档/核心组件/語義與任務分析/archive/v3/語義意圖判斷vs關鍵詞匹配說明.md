# 語義意圖判斷 vs 關鍵詞匹配說明

**版本**: 1.0
**創建日期**: 2026-01-06
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-06

---

## 📋 設計原則

### 核心原則：使用語義意圖判斷，而非關鍵詞匹配

根據 AI-Box 的設計原則，文件編輯功能應該通過 **Task Analyzer 進行語義分析**來判斷意圖，而不是使用簡單的關鍵詞匹配。

---

## 🔍 為什麼不使用關鍵詞匹配？

### 問題 1: 關鍵詞匹配的局限性

**關鍵詞匹配的問題**：

- ❌ 無法理解語義上下文
- ❌ 容易誤判（如「生成」可能是「生成答案」而非「生成文件」）
- ❌ 無法處理多樣化的表達方式
- ❌ 維護成本高（需要不斷添加新關鍵詞）

**示例**：

```python
# ❌ 關鍵詞匹配（錯誤方式）
if "生成文件" in user_text or "產生文件" in user_text:
    # 觸發文件創建
```

**問題**：

- 用戶說「生成答案」→ 誤判為文件生成
- 用戶說「幫我產生一份報告」→ 可能無法匹配（沒有「文件」關鍵詞）
- 用戶說「create a document about Data Agent」→ 無法匹配（英文）

---

### 問題 2: 語義理解的優勢

**語義判斷的優勢**：

- ✅ 理解用戶真實意圖
- ✅ 處理多樣化的表達方式
- ✅ 考慮上下文和語境
- ✅ 自動適應新的表達方式

**示例**：

```python
# ✅ 語義判斷（正確方式）
router_decision = await router_llm.route(user_query)
if router_decision.needs_tools and router_decision.intent_type == "execution":
    # Router LLM 通過語義分析判斷需要文件編輯工具
```

**優勢**：

- 用戶說「生成答案」→ Router LLM 判斷為 `needs_tools=false`（知識問題）
- 用戶說「幫我產生一份報告」→ Router LLM 判斷為 `needs_tools=true`（文件生成）
- 用戶說「create a document about Data Agent」→ Router LLM 判斷為 `needs_tools=true`（文件生成）

---

## 🏗️ 正確的實現方式

### Layer 0: Cheap Gating（快速過濾）

**目的**：快速過濾明顯的簡單查詢（如問候語）

**實現**：

```python
def _is_direct_answer_candidate(self, task: str) -> bool:
    """
    Layer 0: 快速過濾明顯的簡單查詢

    注意：這裡只檢查非常明顯的情況（如問候語），
    複雜意圖（如文件生成）應由 Router LLM 語義分析判斷
    """
    task_lower = task.lower().strip()

    # 只檢查非常明顯的簡單查詢
    if len(task_lower) < 10:
        return True  # 可能是簡單問候語

    # 檢查明顯的動作關鍵詞（僅用於快速過濾）
    action_keywords = ["幫我", "幫", "執行", "運行"]
    if any(keyword in task_lower for keyword in action_keywords):
        return False  # 需要系統行動，進入 Layer 2/3

    # 檢查明確的工具需求（如時間、天氣）
    tool_indicators = ["時間", "天氣", "股價"]
    if any(keyword in task_lower for keyword in tool_indicators):
        return False  # 需要工具，進入 Layer 2/3

    # 默認：嘗試直接回答（讓 Layer 1 的 LLM 判斷）
    return True
```

**關鍵點**：

- ✅ 只檢查非常明顯的情況
- ✅ 不檢查文件生成關鍵詞（由 Router LLM 判斷）
- ✅ 讓 Layer 1 的 LLM 進行初步判斷

---

### Layer 1: Fast Answer Layer（高級 LLM 直接回答）

**目的**：優先使用內部知識庫，如果無法回答則使用高級 LLM

**System Prompt**：

```
Before answering, determine:
1. Does this question require real-time data or external tools?
2. Does this question require accessing internal system state?
3. Does this question require performing actions or operations?
4. Does this question require creating, generating, or editing files/documents?

If YES to any → Respond with ONLY: {"needs_system_action": true}
If NO → Answer the question directly and completely.

Examples:
- "幫我產生Data Agent文件" → {"needs_system_action": true} (requires file creation)
- "生成文件" → {"needs_system_action": true} (requires file creation)
```

**關鍵點**：

- ✅ LLM 通過語義理解判斷是否需要系統行動
- ✅ 明確說明文件生成需要系統行動
- ✅ 如果判斷需要系統行動，返回 `{"needs_system_action": true}`，進入 Layer 2/3

---

### Layer 2: Semantic Intent Analysis（語義意圖分析）

**目的**：使用 Router LLM 進行語義意圖分類

**Router LLM System Prompt**：

```
TOOL REQUIREMENT DETECTION (needs_tools):
Set needs_tools=true if the query requires:
5. Document creation or editing (creating files, generating documents, editing files)

Examples that NEED tools:
- "幫我產生Data Agent文件" → needs_tools=true (requires document editing tool)
- "生成文件" → needs_tools=true (requires document editing tool)
- "幫我將Data Agent的說明做成一份文件" → needs_tools=true (requires document editing tool)
```

**關鍵點**：

- ✅ Router LLM 通過語義分析判斷文件生成意圖
- ✅ 不依賴關鍵詞匹配
- ✅ 能夠理解多樣化的表達方式

---

## 📊 完整流程

### 正確的流程（語義判斷）

```
用戶輸入：「幫我產生Data Agent文件」
    ↓
Layer 0: Cheap Gating
    - 檢查是否為簡單查詢
    - 不是簡單查詢，繼續
    ↓
Layer 1: Fast Answer Layer
    - LLM 判斷：需要系統行動（文件創建）
    - 返回：{"needs_system_action": true}
    - 進入 Layer 2/3
    ↓
Layer 2: Semantic Intent Analysis
    - Router LLM 語義分析
    - 判斷：needs_tools=true, intent_type="execution"
    - 輸出：RouterDecision
    ↓
Layer 3: Decision Engine
    - Capability Matcher 匹配 document_editing 工具
    - Decision Engine 選擇 document_editing 工具
    ↓
文件創建邏輯執行
```

### 錯誤的流程（關鍵詞匹配）

```
用戶輸入：「幫我產生Data Agent文件」
    ↓
Layer 0: 關鍵詞匹配
    - 檢查是否包含「生成文件」關鍵詞
    - 匹配成功，返回 False
    - 進入 Layer 2/3
    ↓
問題：
- 如果用戶說「生成答案」，也會被誤判
- 無法處理多樣化的表達方式
- 維護成本高
```

---

## ✅ 修復記錄

### 2026-01-06 修復

**問題**：

- `_is_direct_answer_candidate` 中添加了文件生成關鍵詞檢查
- 違反了「使用語義判斷而非關鍵詞匹配」的設計原則

**修復**：

1. ✅ 移除文件生成關鍵詞檢查
2. ✅ 增強 Layer 1 的 System Prompt，明確說明文件生成需要系統行動
3. ✅ 確保 Router LLM 能夠正確識別文件生成意圖

**修復後的流程**：

- Layer 0: 只檢查非常明顯的情況（問候語、明確的動作關鍵詞）
- Layer 1: LLM 通過語義理解判斷是否需要系統行動（包括文件生成）
- Layer 2: Router LLM 進行語義意圖分類，判斷文件生成意圖

---

## 🎯 最佳實踐

### 1. 避免關鍵詞匹配

**❌ 錯誤**：

```python
if "生成文件" in user_text or "產生文件" in user_text:
    # 觸發文件創建
```

**✅ 正確**：

```python
router_decision = await router_llm.route(user_query)
if router_decision.needs_tools and router_decision.intent_type == "execution":
    # Router LLM 通過語義分析判斷需要文件編輯工具
```

### 2. 使用語義判斷

**✅ 正確**：

- 使用 Router LLM 進行語義意圖分類
- 使用 Capability Matcher 進行能力匹配
- 使用 Decision Engine 進行綜合決策

### 3. 只在必要時使用關鍵詞匹配

**✅ 可接受**：

- Layer 0 快速過濾明顯的簡單查詢（如問候語）
- 明確的工具需求（如時間、天氣）的快速過濾

**❌ 不可接受**：

- 文件生成等複雜意圖的關鍵詞匹配
- 依賴關鍵詞匹配進行業務邏輯判斷

---

## 📚 相關文檔

- [GenAI 工作流指令-語義-工具-模型-Agent 等調用](./GenAI%20工作流指令-語義-工具-模型-Agent%20等調用.md)
- [通用助理文件編輯問題修復報告](./通用助理文件編輯問題修復報告.md)
- [測試Data任務文件生成問題診斷指南](./測試Data任務文件生成問題診斷指南.md)

---

**最後更新日期**: 2026-01-06
**文檔版本**: 1.0
**維護人**: Daniel Chung
