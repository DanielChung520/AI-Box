# LangChain 上下文管理方式說明

**代碼功能說明**: 說明 LangChain 框架的上下文管理機制，與 AI-Box 上下文管理的比較分析
**創建日期**: 2026-01-23
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-23

---

## 📋 LangChain 記憶系統概述

LangChain 提供了豐富的記憶（Memory）系統來管理對話上下文，主要分為以下幾類：

### 1. 對話記憶（Conversation Memory）
負責存儲和檢索對話歷史，是最常用的記憶類型。

#### 主要實現

| 記憶類型 | 功能描述 | 適用場景 | 優點 | 缺點 |
|---------|---------|---------|------|------|
| **ConversationBufferMemory** | 存儲完整的對話歷史 | 需要完整上下文的場景 | 準確性高 | Token 消耗大 |
| **ConversationSummaryMemory** | 將對話歷史總結為摘要 | 長對話場景 | Token 節省 | 可能丟失細節 |
| **ConversationBufferWindowMemory** | 只保留最近 k 個交互 | 控制上下文長度的場景 | 平衡性能 | 丟失歷史信息 |
| **ConversationSummaryBufferMemory** | 結合摘要和緩衝窗口 | 大多數實際應用 | 平衡各方面 | 複雜度較高 |

#### 使用方式

```python
from langchain.memory import ConversationBufferMemory
from langchain.agents import create_agent

# 創建記憶實例
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True,
    max_token_limit=2000  # 可選：限制 token 數量
)

# 與 Agent 一起使用
agent = create_agent(
    model="gpt-4",
    tools=[tools],
    memory=memory,  # 自動集成記憶
    system_prompt="You are a helpful assistant"
)

# 調用時自動處理記憶
response = agent.invoke({
    "input": "Hello, my name is John"
})
# 記憶自動存儲和檢索
```

### 2. 長期記憶（Long-term Memory）
LangChain 還提供了更進階的長期記憶機制。

#### 主要實現

| 記憶類型 | 功能描述 | 技術基礎 |
|---------|---------|----------|
| **VectorStoreRetrieverMemory** | 基於向量存儲的記憶檢索 | ChromaDB, FAISS 等 |
| **EntityMemory** | 基於實體的記憶管理 | 實體識別和關聯 |
| **ConversationKGMemory** | 基於知識圖譜的記憶 | 圖譜存儲 |

### 3. 自定義記憶（Custom Memory）
LangChain 支持實現自定義記憶類。

```python
from langchain.memory import BaseMemory
from langchain.schema import BaseMessage

class CustomMemory(BaseMemory):
    """自定義記憶實現"""
    
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """保存上下文"""
        # 自定義保存邏輯
        pass
    
    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """加載記憶變數"""
        # 自定義檢索邏輯
        return {}
```

---

## 🔄 LangChain 記憶工作流程

### 典型 Agent 調用流程

```mermaid
graph TD
    A[用戶輸入] --> B[Agent.invoke()]
    B --> C[記憶.load_memory_variables()]
    C --> D[將歷史消息注入 prompt]
    D --> E[LLM 生成回應]
    E --> F[記憶.save_context()]
    F --> G[返回結果]
```

### 記憶注入機制

1. **自動注入**：Agent 自動從記憶中檢索相關歷史
2. **格式化**：將記憶轉換為適合 LLM 的格式
3. **上下文組裝**：將歷史消息與當前輸入組合成完整 prompt

### 記憶更新機制

1. **自動保存**：每次 Agent 調用後自動保存新交互
2. **格式標準化**：統一的輸入/輸出格式
3. **持久化**：根據記憶類型決定存儲方式

---

## 🆚 與 AI-Box 上下文管理的比較

### 架構差異

| 維度 | LangChain Memory | AI-Box 上下文管理 |
|------|-----------------|-------------------|
| **集成方式** | 與 Agent 緊密耦合 | 獨立的三層架構 |
| **記憶範圍** | 主要對話歷史 | 對話 + 文件 + 任務 |
| **存儲方式** | 內存/簡單持久化 | Redis + ArangoDB + Qdrant |
| **檢索機制** | 基於時間順序 | 向量檢索 + 圖譜檢索 |
| **更新時機** | Agent 調用後自動 | 多點觸發（消息、任務、文件） |

### 功能對比

| 功能 | LangChain Memory | AI-Box 上下文管理 |
|------|------------------|-------------------|
| **對話歷史** | ✅ ConversationBufferMemory | ✅ ContextManager |
| **上下文壓縮** | ⚠️ ConversationSummaryMemory | ⚠️ 基礎實現 |
| **向量記憶** | ✅ VectorStoreRetrieverMemory | ✅ Qdrant 集成 |
| **任務關聯** | ❌ 不支持 | ✅ 任務中心化 |
| **多模態記憶** | ❌ 有限支持 | ✅ 文件 + 圖譜記憶 |
| **實時同步** | ✅ Agent 自動 | ✅ 多組件協調 |

### 優缺點分析

#### LangChain Memory 優點
- **簡單易用**：幾行代碼即可集成
- **自動化**：Agent 調用時自動處理
- **標準化**：統一的記憶接口
- **生態豐富**：多種記憶實現

#### LangChain Memory 缺點
- **功能單一**：主要關注對話歷史
- **擴展性差**：難以集成複雜業務邏輯
- **持久化弱**：大多數實現缺乏強健的持久化
- **智能不足**：缺乏進階的記憶管理和檢索

#### AI-Box 上下文管理優點
- **業務集成**：與任務和文件系統深度集成
- **多源記憶**：支持對話、文件、圖譜等多源記憶
- **智能檢索**：向量檢索 + 圖譜推理
- **架構清晰**：分層設計，易於維護

#### AI-Box 上下文管理缺點
- **複雜度高**：需要管理多個組件協調
- **集成成本**：與 Agent 的集成需要額外工作
- **學習成本**：相對於 LangChain 更複雜

---

## 🔧 整合建議

### 階段一：兼容模式

```python
class LangChainAIBridge:
    """LangChain 與 AI-Box 的橋接層"""
    
    def __init__(self, aibox_context_manager, langchain_memory):
        self.aibox = aibox_context_manager
        self.langchain = langchain_memory
    
    def load_memory_variables(self, inputs):
        """同時從兩個系統檢索記憶"""
        # AI-Box 記憶
        aibox_memory = self.aibox.get_context(inputs.get("session_id"))
        
        # LangChain 記憶
        langchain_memory = self.langchain.load_memory_variables(inputs)
        
        # 融合結果
        return self._merge_memories(aibox_memory, langchain_memory)
    
    def save_context(self, inputs, outputs):
        """同時保存到兩個系統"""
        # 保存到 AI-Box
        self.aibox.add_message(inputs.get("session_id"), {
            "role": "assistant",
            "content": outputs.get("output", "")
        })
        
        # 保存到 LangChain
        self.langchain.save_context(inputs, outputs)
```

### 階段二：統一接口

建立統一的記憶管理接口，讓 LangChain Agent 能夠無縫使用 AI-Box 的上下文管理能力。

```python
class UnifiedMemoryAdapter(BaseMemory):
    """統一記憶適配器"""
    
    def __init__(self, aibox_context_manager):
        self.aibox = aibox_context_manager
    
    def load_memory_variables(self, inputs):
        """適配 AI-Box 的記憶檢索"""
        session_id = inputs.get("session_id")
        if session_id:
            context = self.aibox.get_context(session_id)
            return {"chat_history": self._format_context(context)}
        return {}
    
    def save_context(self, inputs, outputs):
        """適配 AI-Box 的記憶保存"""
        session_id = inputs.get("session_id")
        if session_id:
            self.aibox.add_message(session_id, {
                "role": "user", 
                "content": inputs.get("input", "")
            })
            self.aibox.add_message(session_id, {
                "role": "assistant",
                "content": outputs.get("output", "")
            })
```

---

## 📊 結論

### LangChain 的上下文管理哲學

1. **簡單為主**：提供簡單易用的記憶抽象
2. **Agent中心**：記憶系統圍繞 Agent 需求設計
3. **即插即用**：標準化接口，易於替換
4. **功能專注**：專注於對話歷史管理

### AI-Box 的上下文管理哲學

1. **業務導向**：深度集成業務邏輯和數據
2. **多源融合**：整合對話、文件、任務等多源信息
3. **智能檢索**：使用向量和圖譜技術提升檢索質量
4. **架構完整**：分層設計，支持複雜應用場景

### 建議使用策略

| 場景 | 推薦方案 |
|------|----------|
| **簡單 Agent 應用** | LangChain Memory + 基本持久化 |
| **複雜業務系統** | AI-Box 上下文管理 + LangChain 橋接 |
| **漸進式升級** | 先用 LangChain，後集成 AI-Box |
| **混合部署** | 統一接口 + 橋接層 |

---

**文檔版本**: v1.0
**最後更新**: 2026-01-23
**維護人**: Daniel Chung