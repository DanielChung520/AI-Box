# API 路由重构计划：将 MM-Agent 硬编码改为通用外部 Agent 调用

**版本**: 1.0
**创建日期**: 2026-03-04
**备份文件**: `api/routers/chat.py.backup_20260304`

---

## 1. 背景与目的

### 问题描述

当前 `api/routers/chat.py` 中存在大量硬编码的 `mm-agent` 判断逻辑，这违反了 AI-Box 作为 Orchestrator（编排器）的设计原则：

1. **硬编码问题**：代码中判断 `is_mm_agent = user_selected_agent_id.startswith("-")` 或 `user_selected_agent_id == "mm-agent"`
2. **重复代码**：多处重复查询 `agent_display_configs` 获取 endpoint
3. **日志硬编码**：日志中写死 "mm-agent"，不支持其他外部 Agent
4. **变量名硬编码**：使用 `mm_endpoint`、`mm_request` 等特定名称

### 设计原则

AI-Box 是 **Orchestrator（编排器）**，应该：
- **不关心具体是哪个 Agent**：只关心是否为外部 Agent
- **通过配置判断**：是否外部 Agent 由 `agent_display_configs` 中的 `endpoint_url` 决定
- **通用命名**：使用 `agent_endpoint`、`agent_request` 等通用名称

---

## 2. 核心函数

### _get_endpoint_url()

已在文件中添加（Line ~524-575）：

```python
def _get_endpoint_url(agent_key: str) -> Optional[str]:
    """
    根據 agent_key 獲取 endpoint URL
    
    從 agent_display_configs 中查詢配置，返回完整的 endpoint_url
    
    Args:
        agent_key: Agent 的 _key 或 agent_id
    
    Returns:
        endpoint_url 如果找到，否則返回 None
    """
    # 查詢邏輯...
```

**使用方式**：
```python
agent_endpoint = _get_endpoint_url(user_selected_agent_id) if user_selected_agent_id else None

if agent_endpoint:  # 有 endpoint → 外部 Agent → 轉發
    # 調用外部 Agent
else:  # 無 endpoint → 內部 Agent → 走正常流程
    # 執行內部邏輯
```

---

## 3. 需要修改的位置（共 3 处）

### 3.1 第一处：非流式 API（Line ~2440-2510）

**当前问题代码段**：
```python
# Line 2440-2442: 硬编码判断
is_mm_agent = user_selected_agent_id and user_selected_agent_id.startswith("-")
if is_mm_agent or should_forward:
    # ...大量重复代码...
    # Line 2460-2476: 再次查询 agent_display_configs
    from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService
    store = AgentDisplayConfigStoreService()
    agent_config = store.get_agent_config(...)
    # Line 2477-2478: 再次获取 endpoint
    if agent_config and hasattr(agent_config, "endpoint_url"):
        mm_endpoint = agent_config.endpoint_url
        # Line 2486-2503: /auto-execute 硬编码判断
        if "/auto-execute" in mm_endpoint:
            mm_request = {...}
        else:
            mm_request = {...}
```

**修改后**：
```python
# 使用统一函数获取 endpoint
agent_endpoint = _get_endpoint_url(user_selected_agent_id) if user_selected_agent_id else None

if agent_endpoint or should_forward:
    # 统一日志
    sys.stderr.write(f"\n[外部Agent] 🔀 轉發給外部 Agent\n")
    
    # 统一请求格式（标准 /execute 格式）
    agent_request = {
        "task_id": task_id or str(uuid.uuid4()),
        "task_type": "query_stock",
        "task_data": {
            "instruction": last_user_text,
            "user_id": current_user.user_id,
            "session_id": session_id,
        },
    }
    
    # 统一日志
    sys.stderr.write(f"[外部Agent] 📤 調用外部 Agent: endpoint={agent_endpoint}\n")
    
    # 发送请求
    response = httpx.post(agent_endpoint, json=agent_request, ...)
```

### 3.2 第二处：chat 函数（Line ~2800-2920）

**修改内容同 3.1**，需要将 `is_mm_agent_chat` 硬编码改为 `_get_endpoint_url()`

### 3.3 第三处：流式 API（Line ~4250-4450）

**修改内容同 3.1**，需要将 `is_mm_agent` 硬编码改为 `_get_endpoint_url()`

---

## 4. 修改清单

### 4.1 变量名替换

| 旧变量名 | 新变量名 | 说明 |
|---------|---------|------|
| `mm_endpoint` | `agent_endpoint` | 外部 Agent 的 endpoint |
| `mm_request` | `agent_request` | 发送给外部 Agent 的请求 |
| `is_mm_agent` | 删除 | 用 `agent_endpoint` 是否存在判断 |
| `is_mm_agent_chat` | 删除 | 用 `agent_endpoint` 是否存在判断 |
| `mm_result` | `agent_result` | 外部 Agent 的返回结果 |
| `mm-agent` (日志) | `外部Agent` | 通用日志描述 |

### 4.2 删除的重复代码

| 位置 | 删除内容 |
|------|---------|
| ~2460-2476 | 重复的 `from services.api.services... import` 和 `store.get_agent_config()` 查询 |
| ~2486-2503 | `/auto-execute` 硬编码判断（统一使用 `/execute` 格式） |
| 类似位置 | 其他 2 处相同的重复代码 |

### 4.3 日志修改

| 旧日志 | 新日志 |
|--------|--------|
| `[mm-agent] 🔀 轉發給 MM-Agent` | `[外部Agent] 🔀 轉發給外部 Agent` |
| `[mm-agent] 📤 調用 MM-Agent` | `[外部Agent] 📤 調用外部 Agent` |
| `[mm-agent] 🔍 查詢 agent config` | 删除（已通过 `_get_endpoint_url` 获取） |
| `[mm-agent] ❌ 調用失敗` | `[外部Agent] ❌ 調用失敗` |

---

## 5. 修改后的代码结构示例

### 5.1 正确的判断逻辑

```python
# 使用统一函数获取 endpoint，判斷是否為外部 Agent
agent_endpoint = _get_endpoint_url(user_selected_agent_id) if user_selected_agent_id else None

if agent_endpoint or should_forward:
    # ========== 外部 Agent 流程 ==========
    
    # 统一日志
    logger.info(f"[外部Agent] 🔀 轉發給外部 Agent: agent_id={user_selected_agent_id}, endpoint={agent_endpoint}")
    
    # 构建请求（统一格式）
    agent_request = {
        "task_id": task_id or str(uuid.uuid4()),
        "task_type": "query_stock",
        "task_data": {
            "instruction": last_user_text,
            "user_id": current_user.user_id,
            "session_id": session_id,
        },
    }
    
    # 发送请求
    response = httpx.post(agent_endpoint, json=agent_request, timeout=120.0)
    
    # 处理响应
    if response.status_code == 200:
        agent_result = response.json()
        result_text = _parse_agent_response(agent_result)
        return ChatResponse(content=f"【{user_selected_agent_id} 查詢結果】\n{result_text}", ...)
    else:
        logger.error(f"[外部Agent] 調用失敗: HTTP {response.status_code}")
        # 错误处理...

else:
    # ========== 内部 Agent 流程 ==========
    # 原有逻辑不变...
    pass
```

### 5.2 响应解析函数（可选抽取）

```python
def _parse_agent_response(agent_result: dict) -> str:
    """解析外部 Agent 的返回结果"""
    if isinstance(agent_result, dict):
        if "result" in agent_result:
            result_data = agent_result["result"]
            if isinstance(result_data, dict):
                if "response" in result_data:
                    return result_data["response"]
            return str(result_data)
        elif "content" in agent_result:
            return str(agent_result["content"])
    return str(agent_result)
```

---

## 6. 测试计划

### 6.1 测试用例

| 用例 | 输入 | 预期结果 |
|------|------|---------|
| 测试外部 Agent | `agent_id=-h0tjyh`, `message=查NI001的庫存` | 调用 `http://localhost:8003/execute` |
| 测试内部 Agent | `agent_id=ka-agent` (无 endpoint) | 走正常内部逻辑 |
| 测试不存在的 Agent | `agent_id=nonexistent` | 返回错误或走内部逻辑 |

### 6.2 验证点

1. ✅ 日志输出显示 `[外部Agent]` 而非 `[mm-agent]`
2. ✅ 变量名使用 `agent_endpoint`、`agent_request`
3. ✅ 无 `/auto-execute` 硬编码判断
4. ✅ 无重复的 `agent_display_configs` 查询代码

---

## 7. 回滚方案

如需回滚，使用备份文件：
```bash
cp /home/daniel/ai-box/api/routers/chat.py.backup_20260304 /home/daniel/ai-box/api/routers/chat.py
```

---

## 8. 修改优先级

1. **第一优先级**：添加 `_get_endpoint_url()` 函数 ✅ 已完成
2. **第二优先级**：修改第一处（Line ~2440-2510）
3. **第三优先级**：修改第二处（Line ~2800-2920）
4. **第四优先级**：修改第三处（Line ~4250-4450）
5. **第五优先级**：清理响应解析逻辑（可选）

---

**编写人**: AI Agent (Sisyphus)
**审核人**: Daniel Chung
**交付给**: AI Agent Coder
