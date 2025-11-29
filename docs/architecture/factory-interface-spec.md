# Factory 接口規範

## 概述

本文檔定義 AI-Box 專案中所有 Factory 類的統一接口規範，確保一致的設計模式和易於維護。

## 統一 Factory 接口規範

### 核心方法

所有 Factory 類應該實現以下核心方法（根據實際需求選擇）：

#### 1. create() / create_*() - 創建實例

**簽名**：
```python
@staticmethod
def create(item_type: Type, use_cache: bool = True, **kwargs: Any) -> ItemType:
    """
    創建實例。

    Args:
        item_type: 要創建的類型（可選，某些 Factory 可能不需要）
        use_cache: 是否使用緩存（單例模式）
        **kwargs: 初始化參數

    Returns:
        創建的實例

    Raises:
        ValueError: 如果類型不支持
    """
    pass
```

#### 2. get_cached() / get_cached_*() - 獲取緩存實例

**簽名**：
```python
@staticmethod
def get_cached(item_type: Type) -> Optional[ItemType]:
    """
    獲取緩存的實例。

    Args:
        item_type: 要獲取的類型

    Returns:
        緩存的實例，如果不存在返回 None
    """
    pass
```

#### 3. clear_cache() - 清除緩存

**簽名**：
```python
@staticmethod
def clear_cache(item_type: Optional[Type] = None) -> None:
    """
    清除緩存。

    Args:
        item_type: 要清除的類型（如果為 None，清除所有緩存）
    """
    pass
```

#### 4. is_available() / is_*_available() - 檢查可用性

**簽名**：
```python
@staticmethod
def is_available(item_type: Type) -> bool:
    """
    檢查實例是否可用。

    Args:
        item_type: 要檢查的類型

    Returns:
        如果可用返回 True
    """
    pass
```

## 現有 Factory 實現對比

### 1. LLMClientFactory

**位置**：`llm/clients/factory.py`

**實現的方法**：
- ✅ `create_client()` - 創建 LLM 客戶端
- ✅ `get_cached_client()` - 獲取緩存客戶端
- ✅ `clear_cache()` - 清除緩存
- ✅ `is_client_available()` - 檢查客戶端可用性

**緩存機制**：使用類級別字典 `_client_cache`

### 2. AgentFactory

**位置**：`agents/crewai/agent_factory.py`

**實現的方法**：
- ✅ `create_agent()` - 創建 CrewAI Agent
- ❌ `get_cached_agent()` - 未實現
- ❌ `clear_cache()` - 未實現
- ❌ `is_available()` - 未實現

**建議改進**：添加緩存機制和相關方法

### 3. WorkflowFactoryProtocol

**位置**：`agents/workflows/base.py`

**實現的方法**（協議定義）：
- ✅ `create_workflow()` - 創建工作流（協議方法）

**實現類**：
- `CrewAIWorkflowFactory`
- `AutoGenWorkflowFactory`
- `LangChainWorkflowFactory`
- `HybridWorkflowFactory`

### 4. ParserFactory

**位置**：`services/api/processors/parser_factory.py`

**實現的方法**：
- ✅ `create_parser()` - 創建文件解析器
- ❌ `get_cached_parser()` - 未實現
- ❌ `clear_cache()` - 未實現

**建議改進**：添加緩存機制和相關方法

## 最佳實踐

1. **使用緩存**：對於創建成本高的對象，應該使用緩存
2. **線程安全**：如果 Factory 在多線程環境中使用，需要考慮線程安全
3. **資源管理**：緩存應該有大小限制，避免內存泄漏
4. **錯誤處理**：統一的錯誤處理和日誌記錄
5. **文檔**：每個 Factory 都應該有清晰的文檔說明

## 相關文件

- `llm/clients/factory.py` - LLMClientFactory 實現
- `agents/crewai/agent_factory.py` - AgentFactory 實現
- `agents/workflows/base.py` - WorkflowFactoryProtocol 定義
- `services/api/processors/parser_factory.py` - ParserFactory 實現
