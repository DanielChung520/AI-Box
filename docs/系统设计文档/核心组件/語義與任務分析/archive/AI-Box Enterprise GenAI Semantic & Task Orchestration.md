# AI-Box Enterprise GenAI Semantic & Task Orchestration

## Engineering Design Specification (Draft v0.1)

## 1. 設計目標（Design Goals）

### 1.1 系統定位

本系統是一個 **Agent-first Enterprise AI Orchestration Platform**，其核心 GenAI 不僅負責自然語言理解，而是作為：

- 語義理解引擎（Semantic Engine）
- 任務抽象器（Intent & Task Abstraction）
- Agent 能力協調中樞（Capability-Oriented Orchestrator）
### 1.2 核心設計原則

## 2. 整體處理流程總覽（High-Level Pipeline）

```plain text
User / System Input
        ↓
[ L1 ] Semantic Understanding
        ↓
[ L2 ] Intent & Task Abstraction
        ↓
[ L3 ] Capability Mapping & Task Planning
        ↓
[ L4 ] Constraint Validation & Policy Check
        ↓
[ L5 ] Execution + Observation
        ↓
Memory / Feedback / Model Improvement

```

## 3. L1：語義理解層（Semantic Understanding Layer）

### 3.1 職責定義

> 回答「使用者說了什麼」，不回答「要做什麼」

### 3.2 輸入

- 原始自然語言
- 最近對話摘要（context window abstraction）
- 系統模式（design / execution / sandbox）
### 3.3 輸出（Schema 強制）

```json
{
  "topics": ["document", "system_design"],
  "entities": ["Document Editing Agent", "API Spec", "Patch Format"],
  "action_signals": ["design", "refine", "structure"],
  "modality": "instruction",
  "certainty": 0.92
}

```

### 3.4 工程注意事項

- ❌ 不產生 intent
- ❌ 不指定 agent
- ✔ 可多模型 ensemble（提升穩定度）
## 4. L2：意圖與任務抽象層（Intent & Task Abstraction）

### 4.1 Intent 與 Task 的分離

### 4.2 Intent DSL（v0.1）

```plain text
INTENT modify_document {
  domain: "system_architecture"
  target: "Document Editing Agent"
  output_format: ["Engineering Spec"]
  depth: "Advanced"
}

```

### 4.3 Intent 集合設計原則

- 數量限制：20–50
- 必須版本化
- 不允許 runtime 動態生成新 intent
## 5. L3：能力映射與任務規劃（Capability Mapping & Planning）

### 5.1 Capability Registry（核心中樞）

```json
{
  "agent": "DocumentEditingAgent",
  "capabilities": [
    {
      "name": "generate_patch_design",
      "input": "SemanticSpec",
      "output": "PatchPlan"
    },
    {
      "name": "produce_openapi_spec",
      "input": "PatchPlan",
      "output": "OpenAPISpec"
    }
  ],
  "constraints": {
    "environment": "design_only",
    "writes_system": false
  }
}

```

### 5.2 任務規劃輸出（DAG）

```json
{
  "task_graph": [
    { "id": "T1", "capability": "generate_patch_design" },
    { "id": "T2", "capability": "produce_openapi_spec", "depends_on": ["T1"] }
  ]
}

```

### 5.3 設計重點

- Planner 可用 LLM
- Capability 選擇 **不可由 LLM 自行發明**
## 6. L4：執行約束與策略校驗（Policy & Constraint Layer）

### 6.1 驗證項目

### 6.2 輸出

```json
{
  "allowed": true,
  "requires_confirmation": false,
  "risk_level": "low"
}

```

👉 強烈建議 **不用 LLM**

## 7. L5：觀測、回饋與學習（Observation & Learning）

### 7.1 記錄資料結構

```json
{
  "intent": "modify_document",
  "task_count": 2,
  "execution_success": true,
  "user_correction": false,
  "latency_ms": 4200
}

```

### 7.2 用途

- Intent → Task 命中率
- Agent 能力品質評估
- 私有模型微調資料來源（你 EKD Memory 的燃料）
## 8. Orchestrator 核心職責（你設計得非常對）

> Orchestrator 不執行任務

### 僅負責：

- Intent 決策
- Capability 發現
- Task DAG 分派
- Policy Gate
## 9. 常見失敗模式與防禦設計

## 10. 下一階段（v0.2）擴展方向

- Intent → Macro Workflow
- Task Pattern Reuse
- Intent-aware Memory Weighting
- Planner 與私有模型切換
## 後記

AI-Box 做的**不是「Agent 系統」**，而是：

> 一個可以被訓練、被審計、被演進的 AI 任務作業系統

### 我可以下一步直接幫你補的（不用再重新想）

1. ✅ **Intent DSL 完整表（30 個）**
1. ✅ **Semantic / Intent / Planner Prompt 模板**
1. ✅ **Mermaid 工程架構圖**
1. ✅ **Orchestrator pseudo-code（接近 production）**
1. ✅ **這份文檔轉成白皮書版本**
你說一聲「先做哪一個」，我直接進入下一層工程實作。





# 附錄：

## RAG 在語義分析的協作

> **RAG 在你的系統裡「不是用來回答問題」，而是用來「約束與發現能力」**

## 一、方向判定：RAG 在語義分析的協作在架構上是「正確且稀有的」

```plain text
現在：
LLM + RAG → 能力發現 / 架構理解 / 任務約束

未來：
小模型（System-specialized）→ 意圖判定 / 任務規劃

```

這條路線的本質是：

> 先用 RAG 補「知識與結構」，再用小模型學「決策與模式」

這和多數人走的「RAG 當知識庫 → 一直補 prompt」**完全不同**。

✅ 把 RAG 當成 **系統感知層（System Awareness Layer）**

而不是 FAQ 引擎。

## 二、為什麼「一定要先用 RAG」？（而不是直接訓練小模型）

### 1️⃣ AI-Box系統知識「不是語言知識」

你要檢索的是：

- Agent 能力
- Tool 參數
- 系統架構約束
- 執行風險與 policy
這些東西具備特性：

👉 **RAG 是「外部結構記憶」的正解**

### 2️⃣ RAG 能幫你解決「能力幻覺」這個致命問題

在AI-Box系統裡，最大的風險不是回答錯，而是：

> Agent 以為自己能做某件事

若RAG 檢索的是：

- 「系統目前有哪些 agent」
- 「這些 agent 各自能做什麼」
- 「限制條件是什麼」
這代表：

```plain text
沒有被 RAG 檢索到的能力 = 不存在

```

這是一種 **硬邊界（Hard Boundary）**

而不是 prompt 里的「請不要亂做事」。

## 三、注意：這裡用的不是「一般 RAG」，而是「結構型 RAG」

這一段很關鍵，你如果走歪，整個系統會失控。

### ❌ 錯誤用法（常見）

- 把 README / 設計文件丟進 vector DB
- 問：「系統有哪些 agent？」
👉 這會讓 LLM「總結」而不是「發現能力」

### ✅ 正確用法（該用的）

應該把 RAG 的資料切成 **三個明確命名的知識域（Namespaces）**

### 🔹 RAG-1：Architecture Awareness

**用途**：讓 LLM 知道「世界長怎樣」

內容：

- 系統拓撲
- Orchestrator 職責
- Agent 分層
檢索結果是 **背景上下文**，不可直接用於決策。

### 🔹 RAG-2：Capability Discovery（最重要）

**用途**：唯一合法的「能力來源」

每筆資料都要像這樣：

```json
{
  "agent": "DocumentEditingAgent",
  "capability": "generate_patch",
  "inputs": ["SemanticSpec"],
  "outputs": ["PatchPlan"],
  "constraints": ["design_only"]
}

```

👉 **Planner 只能用 RAG-2 的結果**

### 🔹 RAG-3：Policy & Constraint Knowledge

**用途**：防止系統自殺

內容：

- 禁止操作
- 危險操作
- 需要確認的情境
## 四、RAG 在你的流程中「應該插在哪裡」？

對應之前的 5 層架構：

```plain text
L1 Semantic Understanding      ❌ 不用 RAG
L2 Intent Abstraction          ⚠️ 可輕度
L3 Capability Mapping          ✅ 核心使用
L4 Policy Validation           ✅ 必須
L5 Learning                   ❌ 不用

```

🔑 **RAG 不是用來「理解語言」的**

而是用來「限制行為空間」。

## 五、什麼時候「該訓練專屬小模型」？

時機很重要。

### 🔥 過早訓練小模型 = 把錯誤固化

你應該等到以下條件成立：

### ✅ 小模型訓練的成熟信號

1. Intent 分佈穩定（80% 都在那 20–30 個）
1. Task DAG 模式高度重複
1. RAG 命中率高且穩定
1. 人類修正率持續下降
### 🧠 小模型該「專注學什麼」？

不是學知識，而是學：

- Intent 判定
- Task Pattern 選擇
- Planner heuristic
- Risk 預測
👉 **知識仍然放在 RAG / Registry**

## 六、你現在這條路線的「正確最終形態」

```plain text
User Input
   ↓
Small Model → Intent Classification
   ↓
RAG → Capability & Policy Retrieval
   ↓
Planner → Task DAG
   ↓
Rule Engine → Validation
   ↓
Execution

```

LLM（大型）最後只剩下：

- 複雜規劃
- 新情境 fallback
- 語義補充
## 七、總結（可以寫進白皮書的那種）

> RAG is not a knowledge augmentation mechanism,but a capability constraint and system awareness layer.

### 下一步需要補齊的東西（檢討現有AI-Box實際系統差異 ）

1. 📐 **RAG Namespace & Chunk Schema 設計**
1. 🧠 **RAG + Planner Prompt（防幻覺版）**
1. 🔁 **RAG → Small Model 過渡路線圖**
1. 🗂 AI-box**系統專用的 Capability Vector Schema**
1. 🧪 **判斷「該不該訓練小模型」的量化指標**
