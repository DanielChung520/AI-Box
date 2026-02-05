# KA-Agent 授權管理文檔

**代碼功能說明**: KA-Agent 知識庫權限授權管理說明
**創建日期**: 2026-02-03
**創建人**: Daniel Chung
**最後修改日期**: 2026-02-03

---

## 📋 文檔概述

本文檔說明 KA-Agent 知識庫的權限管理機制，包括：
- 權限授予方式（Agent capabilities）
- 權限檢查流程
- 使用場景和示例

---

## 🔐 權限機制設計

### 核心原則

1. **統一入口**: 所有知識庫檢索必須通過 KA-Agent
2. **權限控制**: Agent 需要通過 capabilities 標記獲得權限
3. **未來擴展**: 若檢索升級，只需修改 KA-Agent，其他 Agent 無需調整

### 權限標識

| Capability 名稱 | 說明 | 授權對象 |
| -------------- | ---- | -------- |
| `mm_agent_knowledge` | MM-Agent 知識庫訪問權限 | 需要訪問物料管理知識庫的 Agent |

---

## 📝 權限授予方式

### 方式 1：前端 Agent 卡片編輯（推薦）

**步驟**：
1. 登入 ai-bot 前端
2. 點擊「經寶物料管理代理」卡片
3. 點擊「修改」按鈕
4. 在「能力列表」中點擊「🗄️ MM-Agent 知識庫」快捷按鈕
5. 保存配置

**效果**：
- Agent 的 `capabilities` 列表包含 `"mm_agent_knowledge"`
- 同步到 Agent Registry

### 方式 2：後端 API 直接設置

**API**: `PUT /api/v1/agent-display-configs/agents/{agent_id}`

**請求體**：
```json
{
  "capabilities": ["mm_agent_knowledge"]
}
```

### 方式 3：直接更新 ArangoDB

**Collection**: `agent_display_configs`

**更新示例**：
```javascript
// 在 ArangoDB Web UI 中執行
UPDATE agent_display_configs
  SET agent_config.capabilities = ["mm_agent_knowledge"]
  WHERE agent_config.id == "jingbao-mm-1"
```

---

## 🔍 權限檢查流程

### 流程圖

```
用戶選擇 Agent + 問題
    ↓
Task Analyzer 檢測知識查詢 (Knowledge Signal)
    ↓
Decision Engine 檢查權限
    ├─ 有權限 → 選擇用戶選擇的 Agent
    └─ 無權限 → 選擇 KA-Agent
    ↓
Agent 執行任務
    ├─ 有權限的 Agent → 調用 KA-Agent 檢索
    └─ KA-Agent → 直接檢索
    ↓
返回結果給用戶
```

### 權限檢查代碼位置

**Decision Engine**: `agents/task_analyzer/decision_engine.py:594-647`

```python
if is_knowledge_query and user_selected_agent_id:
    # 檢查用戶選擇的 Agent 是否有知識庫權限
    from agents.services.registry.registry import get_agent_registry
    
    registry = get_agent_registry()
    if registry:
        user_agent_info = registry.get_agent_info(user_selected_agent_id)
        if user_agent_info:
            # 檢查是否有 MM-Agent 知識庫權限
            has_mm_knowledge = "mm_agent_knowledge" in user_agent_info.capabilities
            
            if has_mm_knowledge:
                # 用戶選擇的 Agent 有權限，直接使用該 Agent
                chosen_agent = user_selected_agent_id
                reasoning_parts.append(
                    f"知識庫查詢任務，用戶選擇的 Agent '{user_selected_agent_id}' "
                    f"有 MM-Agent 知識庫權限，優先使用該 Agent"
                )
```

### KA-Agent 權限檢查

**位置**: `agents/builtin/ka_agent/agent.py:554-598`

```python
# Agent 權限檢查（檢查是否有 MM-Agent 知識庫訪問權限）
MM_AGENT_KNOWLEDGE_CAPABILITY = "mm_agent_knowledge"

if caller_agent_id:
    try:
        registry = get_agent_registry()
        agent_info = registry.get_agent_info(caller_agent_id)
        
        if agent_info:
            capabilities = agent_info.capabilities or []
            has_mm_knowledge = MM_AGENT_KNOWLEDGE_CAPABILITY in capabilities
            
            if not has_mm_knowledge:
                feedback = self._error_handler.permission_denied(
                    user_id=caller_agent_id,
                    action="知識庫檢索",
                    resource="MM-Agent 知識庫",
                    reason=f"Agent '{caller_agent_id}' 沒有 '{MM_AGENT_KNOWLEDGE_CAPABILITY}' 能力"
                )
                return KAResponse(success=False, message=formatted_feedback, ...)
```

---

## 📊 使用場景

### 場景 1：有權限的 Agent

**前置條件**：
- 用戶選擇「經寶物料管理代理」
- 「經寶物料管理代理」的 capabilities 包含 `"mm_agent_knowledge"`

**用戶輸入**：
```
物料庫存怎樣？
```

**執行流程**：
1. Knowledge Signal 檢測到知識庫查詢
2. Decision Engine 檢查「經寶物料管理代理」有權限
3. 選擇「經寶物料管理代理」
4. 「經寶物料管理代理」調用 KA-Agent 檢索
5. KA-Agent 驗證權限並執行檢索
6. 「經寶物料管理代理」返回結果

**日誌示例**：
```
Decision Engine: User selected agent jingbao-mm-1 has mm_agent_knowledge capability, using it for knowledge query
[KA-Agent] 🔐 Agent 權限檢查: task_id=xxx, caller_agent_id=jingbao-mm-1, has_mm_knowledge=True
```

### 場景 2：無權限的 Agent

**前置條件**：
- 用戶選擇「某個無權限的 Agent」
- 該 Agent 的 capabilities 不包含 `"mm_agent_knowledge"`

**用戶輸入**：
```
物料庫存怎樣？
```

**執行流程**：
1. Knowledge Signal 檢測到知識庫查詢
2. Decision Engine 檢查「某個無權限的 Agent」無權限
3. 選擇 KA-Agent
4. KA-Agent 執行檢索
5. 返回結果

**日誌示例**：
```
Decision Engine: User selected agent xxx does NOT have mm_agent_knowledge capability, falling back to KA-Agent
Decision Engine: Knowledge query detected, selected KA-Agent: ka-agent (score: 0.95)
```

### 場景 3：未選擇 Agent 的知識庫查詢

**用戶輸入**：
```
知識庫中有多少文件？
```

**執行流程**：
1. Knowledge Signal 檢測到知識庫查詢
2. Decision Engine 無 user_selected_agent_id
3. 選擇 KA-Agent
4. KA-Agent 執行檢索
5. 返回結果

---

## 🔧 權限管理 API

### 獲取 Agent 權限

**API**: `GET /api/v1/agent-display-configs/agents/{agent_id}`

**響應示例**：
```json
{
  "success": true,
  "data": {
    "id": "jingbao-mm-1",
    "name": {"zh_TW": "經寶物料管理代理"},
    "capabilities": ["mm_agent_knowledge"]
  }
}
```

### 更新 Agent 權限

**API**: `PUT /api/v1/agent-display-configs/agents/{agent_id}`

**請求體**：
```json
{
  "capabilities": ["mm_agent_knowledge", "document_editing"]
}
```

### 移除 Agent 權限

**API**: `PUT /api/v1/agent-display-configs/agents/{agent_id}`

**請求體**：
```json
{
  "capabilities": []
}
```

---

## 🎯 設計目標與未來擴展

### 當前設計目標

| 目標 | 實現方式 | 狀態 |
| ---- | -------- | ---- |
| 統一知識庫入口 | 所有檢索通過 KA-Agent | ✅ |
| 權限控制 | Agent capabilities | ✅ |
| 無需調整其他 Agent | 未來升級只修改 KA-Agent | ✅ |

### 未來擴展方向

1. **多知識庫支持**：
   - 添加更多知識庫權限（如 `hr_agent_knowledge`, `finance_agent_knowledge`）
   - 每個 Agent 可以訪問多個知識庫

2. **細粒度權限控制**：
   - 權限過期時間
   - 訪問頻次限制
   - IP 白名單

3. **權限審計**：
   - 記錄所有知識庫訪問
   - 統計使用情況
   - 異常訪問告警

---

## 📚 相關文檔

- [語義與任務分析詳細說明](./語義與任務分析詳細說明.md)
- [Agent Registry 說明](./Agent%20Registry%20說明.md)
- [KA-Agent 實現文檔](./KA-Agent%20實現文檔.md)

---

**文檔版本**: v1.0
**最後更新**: 2026-02-03
**維護人**: Daniel Chung
