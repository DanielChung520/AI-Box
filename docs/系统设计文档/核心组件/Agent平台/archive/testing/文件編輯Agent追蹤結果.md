# 文件編輯 Agent 追蹤結果

**創建日期**: 2026-01-09
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-09

## 文件編輯 Agent 追蹤結果

### 實際使用的 Agent ID

經過追蹤，系統中實際使用的文件編輯 Agent ID 為：

- **Agent ID**: `document-editing-agent`（連字符格式）
- **Agent 類型**: `document_editing`
- **工具名稱**: `document_editing`（下劃線格式，用於前端工具選擇）

### Agent 定義位置

- **文件**: `agents/builtin/document_editing/agent.py`
- **Agent ID**: `self.agent_id = "document-editing-agent"`
- **Agent 類別**: Builtin Agent（內建 Agent）

### 使用位置

1. **Router LLM System Prompt**：
   - 文件：`agents/task_analyzer/router_llm.py`
   - 引用：`document-editing-agent`（在 System Prompt 中明確說明文件編輯任務需要此 Agent）

2. **Capability Matcher**：
   - 文件：`agents/task_analyzer/capability_matcher.py`
   - 匹配邏輯：`if agent.agent_id == "document-editing-agent"`

3. **Decision Engine**：
   - 文件：`agents/task_analyzer/decision_engine.py`
   - 優先選擇邏輯：`chosen_agent = "document-editing-agent"`

4. **前端工具選擇**：
   - 文件：`ai-bot/src/components/AssistantMaintenanceModal.tsx`
   - 工具名稱：`document_editing`（下劃線格式，當 `enableFileEditing=true` 時添加）

5. **API 路由**：
   - 文件：`api/routers/chat.py`
   - 檢查邏輯：`"document_editing" in decision_result.chosen_tools`

### 命名差異說明

系統中存在兩種命名格式：

1. **Agent ID**（後端使用）：
   - 格式：`document-editing-agent`（連字符）
   - 使用位置：Agent Registry、Router LLM、Decision Engine

2. **工具名稱**（前端使用）：
   - 格式：`document_editing`（下劃線）
   - 使用位置：前端工具選擇、`allowed_tools`、API 路由

### System Agent Registry 註冊

文件編輯 Agent 已註冊到 System Agent Registry（ArangoDB）：

- **Collection**: `system_agent_registry`
- **Agent ID**: `document-editing-agent`
- **Agent 類型**: `document_editing`
- **標記**: `is_system_agent=True`
- **狀態**: `online`

## System Agent Registry

### 概述

System Agent Registry 是一個獨立的 Agent 註冊表，專門用於存儲和管理系統內部的支援層 Agent（System Agents）。這些 Agent 不會在前端註冊表中顯示，僅供系統內部調用。

### 支持的 System Agents

1. **安全審計 Agent** (`security-manager-agent`)
   - 類型：`security_audit`
   - 功能：安全審計和管理服務
   - 狀態：✅ 已註冊

2. **Report Agent** (`report-agent`)
   - 類型：`report`
   - 功能：報告生成和管理服務
   - 狀態：⏳ 未來添加

3. **文件編輯 Agent** (`document-editing-agent`)
   - 類型：`document_editing`
   - 功能：文件編輯服務
   - 狀態：✅ 已註冊

4. **其他陸續定義中...**

### 存儲位置

- **數據庫**: ArangoDB
- **Collection**: `system_agent_registry`
- **服務**: `SystemAgentRegistryStoreService`

### 主要特點

1. **獨立存儲**：存儲在 ArangoDB 中，使用獨立的 Collection
2. **自動過濾**：前端查詢時自動過濾 System Agents（`is_system_agent=True`）
3. **系統內部調用**：僅供系統內部調用，不會暴露給前端用戶

### 註冊流程

1. **先註冊到 System Agent Registry（ArangoDB）**：

   ```python
   system_agent_store = get_system_agent_registry_store_service()
   system_agent_store.register_system_agent(
       agent_id="document-editing-agent",
       agent_type="document_editing",
       name="Document Editing Agent",
       ...
   )
   ```

2. **然後註冊到 Agent Registry（內存）**：

   ```python
   registry = get_agent_registry()
   registry.register_agent(request, instance=agent)
   ```

3. **自動標記**：註冊到 Agent Registry 時，系統會自動檢查 System Agent Registry 並標記為 `is_system_agent=True`

### 查詢和過濾

1. **前端查詢**（自動過濾 System Agents）：

   ```python
   agents = registry.list_agents(include_system_agents=False)  # 默認值
   ```

2. **系統內部查詢**（可選包括 System Agents）：

   ```python
   agents = registry.list_agents(include_system_agents=True)
   ```

3. **直接查詢 System Agent Registry**：

   ```python
   system_agent_store = get_system_agent_registry_store_service()
   agent = system_agent_store.get_system_agent("document-editing-agent")
   ```

## 相關文件

- **System Agent Registry Store Service**: `services/api/services/system_agent_registry_store_service.py`
- **Agent Registry 註冊邏輯**: `agents/builtin/__init__.py`
- **Agent Registry 模型**: `agents/services/registry/models.py`
- **Agent Discovery**: `agents/services/registry/discovery.py`
- **System Agent Registry 說明**: `docs/系统设计文档/核心组件/系統管理/System-Agent-Registry-說明.md`

---

**文檔版本**: v1.0
**最後更新**: 2026-01-09
**維護人**: Daniel Chung
