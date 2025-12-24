# Orchestrator 使用場景文檔

## 概述

AI-Box 專案中有兩個 Orchestrator 實現，分別適用於不同的使用場景。本文檔說明它們的差異、使用場景和選擇指南。

## 兩個 Orchestrator 對比

### 1. AgentOrchestrator（基礎協調器）

**位置**：`agents/orchestrator/orchestrator.py`

**設計目標**：

- 簡單的 Agent 協調和任務分發
- 適用於單一框架或簡單的多 Agent 協作
- 輕量級實現，易於使用

**主要功能**：

- Agent 註冊和管理
- 任務提交和分發
- 結果聚合
- 負載均衡（簡單的負載計數）

**適用場景**：

- 簡單的 Agent 協作任務
- 單一框架（如純 CrewAI 或純 AutoGen）
- 不需要複雜的工作流編排
- 快速原型開發

**限制**：

- 不支持多框架混合
- 不支持複雜的工作流狀態管理
- 不支持動態模式切換

**示例**：

```python
from agents.orchestrator.orchestrator import AgentOrchestrator

orchestrator = AgentOrchestrator()

# 註冊 Agent
orchestrator.register_agent(
    agent_id="agent1",
    agent_type="crewai",
    capabilities=["research", "writing"]
)

# 提交任務
task_id = orchestrator.submit_task(
    task="研究並撰寫關於 AI 的報告",
    required_capabilities=["research", "writing"]
)

# 獲取結果
result = orchestrator.get_task_result(task_id)
```

---

### 2. HybridOrchestrator（混合編排器）

**位置**：`agents/workflows/hybrid_orchestrator.py`

**設計目標**：

- 複雜的多框架混合編排
- 支持 AutoGen、LangGraph、CrewAI 之間的動態切換
- 完整的工作流狀態管理和同步

**主要功能**：

- 多框架工作流編排（AutoGen、LangGraph、CrewAI）
- 動態模式切換和故障轉移
- 狀態同步和檢查點管理
- 計劃同步（AutogenPlan ↔ LangGraph State）
- Telemetry 事件追蹤

**適用場景**：

- 複雜的多步驟工作流
- 需要多框架混合使用
- 需要動態切換框架以應對不同階段
- 需要完整的工作流狀態追蹤
- 生產環境的複雜任務

**限制**：

- 實現複雜，學習曲線較高
- 資源消耗較大
- 需要更多配置

**示例**：

```python
from agents.workflows.hybrid_orchestrator import HybridOrchestrator
from agents.workflows.models import WorkflowRequestContext

# 創建請求上下文
ctx = WorkflowRequestContext(
    task_id="task-123",
    task="完成一個複雜的研究項目",
    context={"domain": "AI", "output_format": "report"}
)

# 創建混合編排器
orchestrator = HybridOrchestrator(
    request_ctx=ctx,
    primary_mode="autogen",  # 主要使用 AutoGen
    fallback_modes=["langgraph", "crewai"]  # 備用模式
)

# 執行工作流
result = await orchestrator.run()

# 獲取結果
print(f"狀態: {result.status}")
print(f"輸出: {result.output}")
print(f"使用的模式: {result.state_snapshot.get('current_mode')}")
```

---

## 使用場景指南

### 何時使用 AgentOrchestrator

✅ **適合使用 AgentOrchestrator 的情況**：

1. **簡單的 Agent 協作**
   - 只需要幾個 Agent 協同完成任務
   - 任務流程簡單，不需要複雜的狀態管理

2. **單一框架場景**
   - 只使用一個框架（CrewAI、AutoGen 或 LangGraph）
   - 不需要框架間的切換

3. **快速原型開發**
   - 需要快速驗證想法
   - 不需要完整的生產級功能

4. **資源受限環境**
   - 需要輕量級解決方案
   - 對性能要求不高

**示例場景**：

- 簡單的文檔生成任務（研究 → 撰寫 → 審查）
- 單一框架的問答系統
- 簡單的數據處理流程

---

### 何時使用 HybridOrchestrator

✅ **適合使用 HybridOrchestrator 的情況**：

1. **複雜的多步驟工作流**
   - 任務需要多個階段，每個階段可能需要不同的框架
   - 需要動態調整執行策略

2. **多框架混合需求**
   - 不同階段需要不同框架的優勢
   - 例如：規劃用 AutoGen，執行用 LangGraph，審查用 CrewAI

3. **高可靠性要求**
   - 需要故障轉移機制
   - 需要狀態恢復能力

4. **生產環境**
   - 需要完整的監控和追蹤
   - 需要詳細的執行日誌

**示例場景**：

- 複雜的研究項目（需要規劃、研究、分析、撰寫、審查等多個階段）
- 多階段決策系統（每個階段可能需要不同的框架）
- 需要動態調整策略的長期任務

---

## 選擇決策樹

```
開始
  ↓
任務是否複雜？
  ├─ 否 → 使用 AgentOrchestrator
  └─ 是 ↓
      需要多框架混合？
        ├─ 否 → 使用 AgentOrchestrator
        └─ 是 ↓
            需要動態切換？
              ├─ 否 → 使用 AgentOrchestrator
              └─ 是 → 使用 HybridOrchestrator
```

---

## 遷移指南

### 從 AgentOrchestrator 遷移到 HybridOrchestrator

如果您的任務變得複雜，需要遷移到 HybridOrchestrator：

1. **創建 WorkflowRequestContext**

   ```python
   from agents.workflows.models import WorkflowRequestContext

   ctx = WorkflowRequestContext(
       task_id=task_id,
       task=task_description,
       context=additional_context
   )
   ```

2. **初始化 HybridOrchestrator**

   ```python
   orchestrator = HybridOrchestrator(
       request_ctx=ctx,
       primary_mode="autogen",
       fallback_modes=["langgraph"]
   )
   ```

3. **執行工作流**

   ```python
   result = await orchestrator.run()
   ```

4. **處理結果**

   ```python
   if result.status == "completed":
       output = result.output
       # 處理輸出
   ```

---

## 性能對比

| 特性 | AgentOrchestrator | HybridOrchestrator |
|------|-------------------|-------------------|
| 初始化時間 | 快 | 較慢 |
| 內存占用 | 低 | 較高 |
| 執行開銷 | 低 | 較高 |
| 功能完整性 | 基礎 | 完整 |
| 適用場景 | 簡單任務 | 複雜任務 |

---

## 最佳實踐

1. **從簡單開始**：如果任務簡單，先使用 AgentOrchestrator
2. **按需升級**：當任務變複雜時，再遷移到 HybridOrchestrator
3. **合理選擇模式**：根據任務特性選擇合適的 primary_mode
4. **監控和日誌**：使用 HybridOrchestrator 時，充分利用 telemetry 功能
5. **錯誤處理**：為兩種 Orchestrator 都實現適當的錯誤處理

---

## 相關文件

- `agents/orchestrator/orchestrator.py` - AgentOrchestrator 實現
- `agents/workflows/hybrid_orchestrator.py` - HybridOrchestrator 實現
- `agents/workflows/models.py` - 工作流相關模型定義
- `agents/orchestrator/models.py` - Agent 協調相關模型定義
