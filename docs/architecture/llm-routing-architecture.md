# LLM 路由/負載均衡器層級架構文檔

## 概述

AI-Box 專案中的 LLM 路由和負載均衡功能採用分層架構設計，從任務層級到節點層級，每一層負責不同的路由決策。

## 層級架構圖

```
任務層級 (LLMRouter)
  ↓ 根據任務類型選擇 LLM 提供商
策略層級 (DynamicRouter)
  ↓ 根據策略選擇具體的提供商
提供商層級 (MultiLLMLoadBalancer)
  ↓ 在多個 LLM 提供商間分配負載
節點層級 (LLMNodeRouter)
  ↓ 在本地 Ollama 節點間分配負載
```

## 各層級詳細說明

### 1. 任務層級：LLMRouter

**位置**：`agents/task_analyzer/llm_router.py`

**職責**：

- 根據任務類型（QUERY, EXECUTION, REVIEW, PLANNING, COMPLEX）選擇合適的 LLM 提供商
- 整合任務分類結果和上下文信息
- 支持 A/B 測試和路由評估

**主要功能**：

- `route()`: 根據任務分類結果選擇 LLM 提供商
- 支持新舊兩種路由策略（可切換）
- 整合 DynamicRouter、RoutingEvaluator、ABTestManager

**使用場景**：

- 任務分析後的路由選擇
- 需要根據任務特性選擇最適合的 LLM

**示例**：

```python
from agents.task_analyzer.llm_router import LLMRouter
from agents.task_analyzer.models import TaskClassificationResult, TaskType

router = LLMRouter()
result = router.route(
    task_classification=TaskClassificationResult(
        task_type=TaskType.QUERY,
        confidence=0.9
    ),
    task="查詢用戶信息",
    context={"user_id": "123"}
)
```

---

### 2. 策略層級：DynamicRouter

**位置**：`llm/routing/dynamic.py`

**職責**：

- 管理多種路由策略（TaskTypeBased, ComplexityBased, CostBased, LatencyBased, Hybrid）
- 根據配置動態選擇和切換策略
- 記錄路由決策用於評估和優化

**主要功能**：

- `get_strategy()`: 獲取指定的路由策略
- `register_strategy()`: 註冊新的路由策略
- `record_request()`: 記錄路由請求用於統計

**支持的路由策略**：

- `TaskTypeBasedStrategy`: 基於任務類型
- `ComplexityBasedStrategy`: 基於任務複雜度
- `CostBasedStrategy`: 基於成本考慮
- `LatencyBasedStrategy`: 基於延遲要求
- `HybridRoutingStrategy`: 混合策略

**使用場景**：

- 需要根據不同條件選擇路由策略
- 需要動態調整路由行為

**示例**：

```python
from llm.routing.dynamic import DynamicRouter

router = DynamicRouter(default_strategy="hybrid")
strategy = router.get_strategy("task_type_based")
result = strategy.select_provider(task_classification, task, context)
```

---

### 3. 提供商層級：MultiLLMLoadBalancer

**位置**：`llm/load_balancer.py`

**職責**：

- 在多個 LLM 提供商（ChatGPT, Gemini, Grok, Qwen, Ollama）間分配負載
- 實現多種負載均衡策略
- 監控提供商健康狀態和性能指標

**主要功能**：

- `select_provider()`: 根據策略選擇提供商
- `mark_success()` / `mark_failure()`: 標記請求成功/失敗
- `get_provider_stats()`: 獲取提供商統計信息

**支持的負載均衡策略**：

- `round_robin`: 輪詢
- `weighted`: 加權輪詢
- `least_connections`: 最少連接
- `latency_based`: 基於延遲
- `response_time_based`: 基於響應時間

**使用場景**：

- 需要在多個 LLM 提供商間分配請求
- 需要監控和優化提供商使用情況

**示例**：

```python
from llm.load_balancer import MultiLLMLoadBalancer
from agents.task_analyzer.models import LLMProvider

balancer = MultiLLMLoadBalancer(
    providers=[LLMProvider.CHATGPT, LLMProvider.GEMINI, LLMProvider.OLLAMA],
    strategy="weighted",
    weights={LLMProvider.CHATGPT: 3, LLMProvider.GEMINI: 2, LLMProvider.OLLAMA: 1}
)
provider = balancer.select_provider()
```

---

### 4. 節點層級：LLMNodeRouter

**位置**：`llm/router.py`

**職責**：

- 在本地 Ollama 多個節點間分配負載
- 實現節點健康檢查和故障轉移
- 支持輪詢和加權輪詢策略

**主要功能**：

- `select_node()`: 選擇可用的 Ollama 節點
- `mark_success()` / `mark_failure()`: 標記節點狀態
- `get_nodes()`: 獲取節點快照

**支持的負載均衡策略**：

- `round_robin`: 輪詢（默認）
- `weighted`: 加權輪詢

**使用場景**：

- 本地部署多個 Ollama 節點
- 需要在節點間分配請求負載

**示例**：

```python
from llm.router import LLMNodeRouter, LLMNodeConfig

router = LLMNodeRouter(
    nodes=[
        LLMNodeConfig(name="node1", host="localhost", port=11434, weight=2),
        LLMNodeConfig(name="node2", host="localhost", port=11435, weight=1),
    ],
    strategy="weighted",
    cooldown_seconds=30
)
node = router.select_node()
```

---

## 層級關係與組合使用

### 典型使用流程

1. **任務分析** → `LLMRouter.route()` 根據任務類型選擇提供商
2. **策略選擇** → `DynamicRouter.get_strategy()` 獲取路由策略
3. **提供商選擇** → `MultiLLMLoadBalancer.select_provider()` 選擇具體提供商
4. **節點選擇** → 如果選擇 Ollama，`LLMNodeRouter.select_node()` 選擇節點

### 組合示例

```python
# 1. 任務層級：選擇 LLM 提供商
llm_router = LLMRouter()
routing_result = llm_router.route(task_classification, task, context)

# 2. 如果選擇 Ollama，使用節點層級選擇具體節點
if routing_result.provider == LLMProvider.OLLAMA:
    node_router = LLMNodeRouter(nodes=ollama_nodes)
    node = node_router.select_node()
```

---

## 設計原則

1. **單一職責**：每個層級只負責一個特定的路由決策
2. **層級分離**：不同層級可以獨立使用或組合使用
3. **可擴展性**：易於添加新的路由策略或負載均衡算法
4. **可觀測性**：每個層級都提供統計和監控功能

---

## 注意事項

1. **層級選擇**：根據實際需求選擇合適的層級，不需要使用所有層級
2. **性能考慮**：多層級路由會增加延遲，需要權衡
3. **配置管理**：各層級的配置需要統一管理，避免衝突
4. **錯誤處理**：每一層都需要適當的錯誤處理和降級策略

---

## 相關文件

- `agents/task_analyzer/llm_router.py` - LLMRouter 實現
- `llm/routing/dynamic.py` - DynamicRouter 實現
- `llm/load_balancer.py` - MultiLLMLoadBalancer 實現
- `llm/router.py` - LLMNodeRouter 實現
- `llm/routing/strategies.py` - 各種路由策略實現
