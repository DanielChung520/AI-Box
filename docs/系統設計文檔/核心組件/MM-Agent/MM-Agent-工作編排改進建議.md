# MM-Agent 工作編排與執行改進建議

**創建日期**: 2026-02-07
**創建人**: OpenCode AI

---

## 一、背景與問題描述

### 1.1 現況

MM-Agent 目前使用 ReAct 模式進行工作編排，但在實際測試中發現以下問題：

- 工作編排顆粒度不足，生成的步驟過於模糊
- Data-Agent 無法理解模糊的指令
- 步驟間的數據傳遞和執行邏輯不完整

### 1.2 測試案例

**用戶指令**: 「請對我的庫存數據執行 ABC 分類」

**預期結果**: 完整的 ABC 分類報告，包含 A/B/C 三類料號清單

---

## 二、核心設計原則 ✅ 已確認

### 2.1 MM-Agent Schema 不可知原則 ✅ 已確認

MM-Agent **不涉及 schema**，以確保未來 schema 變更時無需修改 MM-Agent。

```
MM-Agent（業務邏輯層）
├── ✅ 知道：要做什麼（ABC 分類）
├── ✅ 知道：需要什麼數據（料號、庫存價值）
├── ✅ 知道：用途是什麼（用於 ABC 分類）
└── ❌ 不知道：schema（表格、字段、JOIN 邏輯）

Data-Agent（數據層）
├── ✅ 知道：schema（img_file, prc_file, 字段）
├── ✅ 知道：如何查詢（JOIN、GROUP BY）
└── ❌ 不知道：業務邏輯
```

**好處：關注點分離**

| 變更 | MM-Agent | Data-Agent |
|------|----------|------------|
| 新增表格 | ❌ 不需修改 | ✅ 更新 schema |
| 字段改名 | ❌ 不需修改 | ✅ 更新映射 |
| 業務邏輯變更 | ✅ 修改 Prompt | ❌ 不需修改 |

### 2.2 編排顆粒度原則 ✅ 已確認

MM-Agent 生成的指令必須包含：
- **需要什麼數據**（料號、庫存數量、單價）
- **做什麼計算**（數量 × 單價 = 庫存價值）
- **用途是什麼**（用於 ABC 分類）

**測試驗證**：

| 指令 | Data-Agent 回應 |
|------|-----------------|
| 「請對我的庫存數據執行 ABC 分類」 | ❌ SQL 截斷，語法錯誤 |
| 「查詢每個料號的庫存數量(mb005)和單價(mb010)，我需要計算庫存價值=數量×單價，按價值降序排列，用於 ABC 分類」 | ✅ 成功返回正確 SQL 和數據 |

---

## 三、核心問題診斷

經過測試與討論，確認三個核心問題：

### 問題 3：LLM 的編排能力

| 面向 | 現況 | 改進方向 |
|------|------|----------|
| 意圖識別 | 只能識別簡單意圖 | 提供上下文讓 LLM 理解複雜任務 |
| 步驟生成 | 生成模糊步驟（如「查詢數據」） | 生成具體可執行的步驟 |
| 格式規範 | 無固定格式 | 提供 JSON Schema 和範例 |

### 問題 4：編排顆粒度

**測試結果**:

| 指令 | Data-Agent 回應 |
|------|-----------------|
| 「請對我的庫存數據執行 ABC 分類」 | SQL 截斷，語法錯誤 |
| 「查詢每個料號的庫存數量(mb005)和單價(mb010)，我需要計算庫存價值=數量×單價，按價值降序排列，用於 ABC 分類」 | ✅ 成功返回正確 SQL 和數據 |

**關鍵洞察**: 指令必須包含
- 需要什麼數據（料號、庫存數量、單價）
- 做什麼計算（數量 × 單價 = 庫存價值）
- 用途是什麼（用於 ABC 分類）

### 問題 5：執行能力

**職責分工**:

```
MM-Agent（業務邏輯）
├── 將業務需求轉換為自然語言指令
├── 生成工作流計劃
└── 整合結果生成報告

Data-Agent（數據查詢）
├── 理解自然語言指令
├── 執行 Text-to-SQL
└── 返回結構化數據

LLM（知識與計算）
├── 檢索領域知識
├── 執行 ABC 分類計算
└── 生成最終報告
```

---

## 三、解決方案架構

### 3.1 工作流設計

**ABC 分類完整工作流**:

```
┌─────────────────────────────────────────────────────────────┐
│ 用戶：「請對我的庫存數據執行 ABC 分類」                       │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 知識檢索                                             │
│ 指令：「請提供 ABC 分類的方法論」                            │
│ 調用：LLM                                                    │
│ 輸出：ABC 分類定義、計算邏輯                                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 數據查詢                                             │
│ 指令：「查詢每個料號的庫存數量(mb005)和單價(mb010)，        │
│       我需要計算庫存價值=數量×單價，按價值降序排列，         │
│       用於 ABC 分類」                                        │
│ 調用：Data-Agent                                             │
│ 輸出：料號、庫存數量、單價、庫存價值列表                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 3: ABC 分類計算                                         │
│ 指令：「根據以下庫存價值列表，執行 ABC 分類：                │
│       A類=累積價值前 70%                                    │
│       B類=累積價值 70-90%                                    │
│       C類=累積價值 90-100%」                                 │
│ 調用：LLM                                                    │
│ 輸出：{"A類": [...], "B類": [...], "C類": [...]}              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 生成報告                                             │
│ 指令：「根據 ABC 分類結果，生成最終報告」                    │
│ 調用：LLM                                                    │
│ 輸出：完整的 ABC 分類報告（含清單、統計、建議）              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Prompt 設計原則

#### 原則 1：提供完整上下文

```python
"""
你是一個工作流編排專家。根據用戶需求，生成具體的數據分析計劃。

【可用工具】
- Data-Agent：執行數據查詢（Text-to-SQL）
- LLM：執行計算和生成報告

【工作流格式】
每個步驟必須包含：
- action_type: 步驟類型（knowledge_retrieval/data_query/computation/response_generation）
- instruction: 具體指令（必須包含：需要什麼數據、做什麼計算、用途）
- parameters: 額外參數
"""
```

#### 原則 2：指令必須具體

| ❌ 錯誤示例 | ✅ 正確示例 |
|-------------|-------------|
| 「查詢數據」 | 「查詢每個料號的庫存數量和單價，我需要計算庫存價值=數量×單價，按價值降序排列，用於 ABC 分類」 |
| 「執行計算」 | 「根據庫存價值列表，執行 ABC 分類：A類=累積價值前 70%，B類=70-90%，C類=90-100%」 |

#### 原則 3：格式規範

```json
{
  "task_type": "data_analysis",
  "steps": [
    {
      "step_id": 1,
      "action_type": "knowledge_retrieval",
      "description": "檢索 ABC 分類知識",
      "instruction": "請提供 ABC 分類的方法論和計算邏輯",
      "parameters": {}
    },
    {
      "step_id": 2,
      "action_type": "data_query",
      "description": "查詢庫存價值",
      "instruction": "查詢每個料號的庫存數量(mb005)和單價(mb010)，我需要計算庫存價值=數量×單價，按價值降序排列，用於 ABC 分類",
      "parameters": {}
    },
    {
      "step_id": 3,
      "action_type": "computation",
      "description": "執行 ABC 分類",
      "instruction": "根據以下庫存價值列表，執行 ABC 分類：A類=累積價值前 70%，B類=70-90%，C類=90-100%",
      "parameters": {}
    },
    {
      "step_id": 4,
      "action_type": "response_generation",
      "description": "生成 ABC 分類報告",
      "instruction": "根據 ABC 分類結果，生成包含 A/B/C 三類清單、統計摘要和管理建議的報告",
      "parameters": {}
    }
  ]
}
```

---

## 四、實作建議

### 4.1 修改 react_planner.py

**目標**: 讓 LLM 生成具體、可執行的工作流

**關鍵修改**:

```python
async def plan(self, instruction: str, context: Optional[Dict[str, Any]] = None) -> TodoPlan:
    # 提供完整上下文和格式範例
    user_prompt = f"""用戶指令：{instruction}

這是一個數據分析任務，請生成包含具體指令的工作計劃。

【要求】
1. 每個步驟必須包含具體、可執行的指令
2. 指令必須說明：需要什麼數據、做什麼計算、用途是什麼
3. 只返回 JSON 格式

【格式範例】
{{"task_type": "data_analysis", "steps": [{{"action_type": "...", "description": "...", "instruction": "具體指令"}}]}}"""

    # 調用 LLM 生成計劃
    plan_json = await self._call_llm(user_prompt)
    return self._parse_plan(instruction, plan_json)
```

### 4.2 修改 react_executor.py

**目標**: 正確執行每個步驟，正確傳遞數據

**關鍵修改**:

```python
async def execute_step(self, action: Action, ...) -> ExecutionResult:
    
    if action.action_type == "knowledge_retrieval":
        # 調用 LLM 檢索知識
        return await self._execute_knowledge_retrieval(action)
        
    elif action.action_type == "data_query":
        # 調用 Data-Agent，傳遞完整指令
        return await self._execute_data_query(action)
        
    elif action.action_type == "computation":
        # 調用 LLM 執行計算
        return await self._execute_computation(action, previous_results)
        
    elif action.action_type == "response_generation":
        # 整合所有結果，調用 LLM 生成報告
        return await self._execute_response_generation(action, previous_results)
```

### 4.3 數據傳遞設計

```python
# Step 2 結果
{
    "query_result": [
        {"料號": "10-0010", "庫存價值": 2176632830.95},
        {"料號": "10-0006", "庫存價值": 1573611688.20},
        ...
    ]
}

# Step 3 輸入（包含 Step 2 結果）
{
    "query_result": [...],
    "instruction": "根據以下庫存價值列表，執行 ABC 分類..."
}

# Step 3 結果
{
    "analysis_result": {
        "A類": ["10-0010", "10-0006", "10-0003", "10-0015", "10-0013"],
        "B類": ["RM04-010", "10-0005", "RM02-005"],
        "C類": ["RM02-010", "10-0007"]
    }
}

# Step 4 輸入（包含所有結果）
{
    "knowledge": "ABC 分類知識...",
    "query_result": [...],
    "analysis_result": {...}
}
```

---

## 五、測試驗證清單

### 5.1 單元測試

- [ ] LLM 能識別意圖並生成正確的 task_type
- [ ] 每個步驟的指令都具體且可執行
- [ ] 步驟間的依賴關係正確
- [ ] 數據傳遞正確

### 5.2 整合測試

- [ ] Step 1: 知識檢索返回正確的 ABC 分類方法論
- [ ] Step 2: Data-Agent 能理解指令並返回正確的 SQL 和數據
- [ ] Step 3: LLM 能根據列表正確執行 ABC 分類
- [ ] Step 4: 生成完整的 ABC 分類報告

### 5.3 端到端測試

```bash
# 測試指令
curl -X POST http://localhost:8003/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-e2e-001", "instruction": "請對我的庫存數據執行 ABC 分類"}'

# 驗證結果
- response 包含 ABC 分類知識
- data_query 返回正確的庫存價值列表
- computation 返回 A/B/C 三類清單
- response_generation 返回完整報告
```

---

## 六、優先級建議

| 優先級 | 任務 | 說明 |
|--------|------|------|
| P0 | 修改 react_planner.py | 讓 LLM 生成具體指令 |
| P0 | 修改 react_executor.py | 正確執行每個步驟 |
| P1 | 實現 computation 步驟 | LLM ABC 分類計算 |
| P2 | 完善錯誤處理 | 指令不清時回問用戶 |
| P2 | 添加測試案例 | 覆蓋更多場景 |

---

## 七、參考資料

- ReAct 模式文獻：https://react-lm.github.io/
- MM-Agent 現有架構：`/home/daniel/ai-box/datalake-system/mm_agent/chain/`
- Data-Agent API：`/home/daniel/ai-box/AGENTS.md`
- ABC 分類方法論：https://en.wikipedia.org/wiki/ABC_analysis

---

## 八、附錄：測試記錄

### 8.1 Data-Agent 測試

**指令**: 「查詢每個料號的庫存數量(mb005)和單價(mb010)，我需要計算庫存價值=數量×單價，按價值降序排列，用於 ABC 分類」

**結果**: ✅ 成功

```sql
SELECT 
    img.img01 AS material,
    SUM(CAST(img.img10 AS DECIMAL)) AS quantity,
    MAX(CAST(prc.prc02 AS DECIMAL)) AS unit_price,
    SUM(CAST(img.img10 AS DECIMAL)) * MAX(CAST(prc.prc02 AS DECIMAL)) AS inventory_value
FROM read_parquet('s3://tiptop-raw/raw/v1/img_file/year=*/month=*/data.parquet', hive_partitioning=true) AS img
LEFT JOIN read_parquet('s3://tiptop-raw/raw/v1/prc_file/year=*/month=*/data.parquet', hive_partitioning=true) AS prc
    ON img.img01 = prc.prc01
WHERE prc.prc04 = 'Y'
GROUP BY img.img01
ORDER BY inventory_value DESC
LIMIT 10;
```

### 8.2 LLM ABC 分類測試

**輸入**: 庫存價值列表（前 10 名）

**結果**: ✅ 成功

```json
{
  "A類": ["10-0010", "10-0006", "10-0003", "10-0015", "10-0013"],
  "B類": ["RM04-010", "10-0005", "RM02-005"],
  "C類": ["RM02-010", "10-0007"],
  "分類說明": "A類包含累積價值前 70% 的料號，共 5 件..."
}
```

---

**文件結束**
