# MoE系统（Mixture of Experts）架构文档

**创建日期**: 2025-12-25
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-25

---

## 📋 概述

MoE（Mixture of Experts，专家模型混合）系统是 AI-Box 的多模型路由架构，根据任务类型和特性动态选择最适合的专家模型。系统支持多个 LLM Provider，通过任务分类与路由策略，实现最优的模型选择与成本控制。

> **相关文档**：
>
> - [LLM路由架构文档](../../備份與歸檔/architecture/llm-routing-architecture.md)
> - [GenAI主计划](../../開發過程文件/plans/genai/GENAI_MASTER_PLAN.md)

---

## 🏗️ 架构设计

### Multi-model 架构

系统支持多个 LLM Provider（Ollama、OpenAI、Anthropic、Qwen等），通过动态路由选择最适合的模型。

### 多模型架构核心原则

**重要**：系统采用多模型架构，不同的工作使用不同的模型。

1. **任务分析和语义理解（L1-L2层）**：
   - ✅ **始终使用本地模型（Ollama）**，不受前端选择的模型影响
   - ✅ 用于内部处理：语义理解、意图分析、任务分类
   - ✅ 实现位置：`agents/task_analyzer/router_llm.py`
   - ✅ 默认模型：`gpt-oss:120b-cloud`（可通过 `ROUTER_LLM_MODEL` 环境变量配置）

2. **前端聊天框选择的模型**：
   - ✅ 只用于最终任务执行和补全
   - ✅ 用于交付任务（任务描述的最終補全）
   - ✅ 用于上网和内部信息无关的模型调用（需要外部API的模型）
   - ✅ 用于最终输出生成

**设计原因**：

- 任务分析和语义理解是内部处理，不需要外部API，使用本地模型更快速、成本更低
- 前端选择的模型用于最终输出，可以根据任务需求选择最适合的模型（如需要联网搜索时使用支持工具的模型）

### 架构图

```mermaid
graph TB
    subgraph TaskAnalysis["任务分析"]
        TaskAnalyzer[Task Analyzer<br/>任务分类]
        TaskClassification[任务分类结果]
    end

    subgraph MoEManager["MoE管理器"]
        DynamicRouter[Dynamic Router<br/>动态路由]
        LoadBalancer[Multi LLM Load Balancer]
        FailoverManager[Failover Manager<br/>故障转移]
    end

    subgraph Providers["LLM Providers"]
        Ollama[Ollama<br/>本地模型]
        OpenAI[OpenAI]
        Anthropic[Anthropic]
        Qwen[Qwen]
    end

    TaskAnalyzer --> TaskClassification
    TaskClassification --> DynamicRouter
    DynamicRouter --> LoadBalancer
    LoadBalancer --> Ollama
    LoadBalancer --> OpenAI
    LoadBalancer --> Anthropic
    LoadBalancer --> Qwen
    FailoverManager --> LoadBalancer

    classDef analysis fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef moe fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef providers fill:#fff3e0,stroke:#e65100,stroke-width:2px

    class TaskAnalyzer,TaskClassification analysis
    class DynamicRouter,LoadBalancer,FailoverManager moe
    class Ollama,OpenAI,Anthropic,Qwen providers
```

---

## 🔧 核心组件

### 1. 任务分类

**功能**：分析任务类型（QUERY、EXECUTION、REVIEW、PLANNING、COMPLEX）

**实现位置**：`agents/task_analyzer/classifier.py`

### 2. 动态路由

**功能**：根据任务分类结果选择最适合的 Provider 和模型

**路由策略**：

- TaskTypeBased：基于任务类型
- ComplexityBased：基于任务复杂度
- CostBased：基于成本考虑
- LatencyBased：基于延迟要求
- Hybrid：混合策略

**实现位置**：`llm/routing/dynamic.py`

### 3. 负载均衡

**功能**：在多个 Provider 和模型间分配负载

**策略**：

- 轮询（Round Robin）
- 加权轮询（Weighted Round Robin）
- 最少连接（Least Connections）

**实现位置**：`llm/load_balancer.py`

### 4. 故障转移

**功能**：Provider 故障时自动切换到备用 Provider

**实现位置**：`llm/failover.py`

---

## 📊 实现状态

### 已完成功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| MoE 管理器 | ✅ 已实现 | `llm/moe/moe_manager.py` |
| 动态路由 | ✅ 已实现 | 多种路由策略 |
| 负载均衡 | ✅ 已实现 | 多 Provider 负载均衡 |
| 故障转移 | ✅ 已实现 | 自动故障转移 |
| 任务分类集成 | ✅ 已实现 | 与 Task Analyzer 集成 |

---

## 📚 参考资料

### 相关文档

- [LLM路由架构文档](../../備份與歸檔/architecture/llm-routing-architecture.md)
- [GenAI主计划](../../開發過程文件/plans/genai/GENAI_MASTER_PLAN.md)

### 代码位置

- MoE 管理器：`llm/moe/moe_manager.py`
- 动态路由：`llm/routing/dynamic.py`
- 负载均衡：`llm/load_balancer.py`
- 故障转移：`llm/failover.py`

---

**最后更新日期**: 2025-12-25
