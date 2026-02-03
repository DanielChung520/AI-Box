# KA-Agent P0 测试问题修复报告

**修复日期**: 2026-01-28 12:00 UTC+8

---

## 修复摘要

根据 `KA-Agent-P0測試報告.md` 第三轮测试发现的问题，已完成以下修复：

### 问题 1: KA-Agent 实例未注册（导致 500 错误）✅ 已修复

**修复内容**：

1. **`agents/builtin/__init__.py` - `_register_agent_helper` 函数**：
   - 添加实例检查：如果 `agent` 为 `None`，记录错误并提前返回
   - 添加注册前日志：记录正在注册的 Agent 和实例类型
   - 添加注册后验证：验证实例是否成功存储到 registry

2. **`agents/builtin/__init__.py` - KA-Agent 注册部分**：
   - 添加诊断日志：在注册前检查 KA-Agent 实例是否存在
   - 记录实例类型和 agent_id

3. **`agents/services/registry/registry.py` - `register_agent` 方法**：
   - 将内部 Agent 缺少实例的警告改为错误（因为内部 Agent 必须提供实例）
   - 添加实例存储后的验证日志，记录实例类型

### 问题 2: 空查询返回 422 错误（而非友好错误消息）✅ 已修复

**修复内容**：

1. **`api/main.py` - `validation_exception_handler` 函数**：
   - 添加空查询检测：检查是否是 `/chat` 端点的空查询错误
   - 检查 `messages[].content` 的 `min_length` 验证错误
   - 使用 KA-Agent 的错误处理器生成友好错误消息
   - 返回 400 错误（而非 422）和友好的用户消息

---

## 修复详情

### 修复 1: KA-Agent 实例注册增强

**文件**: `agents/builtin/__init__.py`

**修改位置**:
- `_register_agent_helper` 函数（第 160-260 行）
- KA-Agent 注册部分（第 703-721 行）

**关键修改**:

```python
# 1. 添加实例检查
if not agent:
    logger.error(
        f"Agent '{agent_key}' not found in agents_dict. Cannot register {agent_id} ({name})."
    )
    return

# 2. 添加注册前日志
logger.info(
    f"Registering {name} ({agent_id}) with instance: {type(agent).__name__}"
)

# 3. 添加注册后验证
stored_instance = registry.get_agent(agent_id)
if stored_instance:
    logger.info(
        f"✅ {name} ({agent_id}) instance stored successfully: "
        f"{type(stored_instance).__name__}"
    )
else:
    logger.warning(
        f"⚠️ {name} ({agent_id}) registered but instance not found in registry."
    )

# 4. KA-Agent 注册前诊断
ka_agent = agents_dict.get("ka_agent")
if ka_agent:
    logger.info(
        f"✅ KA-Agent instance found: {type(ka_agent).__name__}, "
        f"agent_id={ka_agent.agent_id if hasattr(ka_agent, 'agent_id') else 'N/A'}"
    )
else:
    logger.error("❌ KA-Agent instance not found in agents_dict!")
```

### 修复 2: Registry 错误处理增强

**文件**: `agents/services/registry/registry.py`

**修改位置**: `register_agent` 方法（第 100-145 行）

**关键修改**:

```python
# 1. 将警告改为错误
if request.endpoints.is_internal and not instance:
    self._logger.error(
        f"Internal agent '{request.agent_id}' registered without instance. "
        f"Instance is required for internal agents. Registration may fail."
    )

# 2. 添加验证日志
if request.endpoints.is_internal and instance:
    self._agent_instances[request.agent_id] = instance
    self._logger.info(
        f"✅ Stored agent instance for internal agent '{request.agent_id}': "
        f"{type(instance).__name__}"
    )
```

### 修复 3: 空查询错误处理

**文件**: `api/main.py`

**修改位置**: `validation_exception_handler` 函数（第 313-360 行）

**关键修改**:

```python
# 检查是否是 chat 端点的空查询错误
if request.url.path.endswith("/chat") and request.method == "POST":
    # 检查是否是 messages[].content 的 min_length 错误
    is_empty_query = False
    for error in error_details:
        error_loc = error.get("loc", [])
        error_type = error.get("type", "")
        
        if (
            len(error_loc) >= 4
            and error_loc[0] == "body"
            and error_loc[1] == "messages"
            and isinstance(error_loc[2], int)
            and error_loc[3] == "content"
            and "min_length" in error_type
        ):
            is_empty_query = True
            break
    
    if is_empty_query:
        # 使用 KA-Agent 的错误处理器生成友好错误消息
        from agents.builtin.ka_agent.error_handler import KAAgentErrorHandler
        
        error_feedback = KAAgentErrorHandler.missing_parameter(
            parameter="instruction",
            context="用戶查詢為空",
        )
        
        # 返回友好错误消息（使用 400 而非 422）
        return JSONResponse(
            status_code=400,
            content=APIResponse.error(
                message=error_feedback.user_message,
                details={
                    "error_type": error_feedback.error_type.value,
                    "suggested_action": error_feedback.suggested_action.value,
                    "clarifying_questions": error_feedback.clarifying_questions,
                },
            ).model_dump(),
        )
```

---

## 预期效果

### 修复前

1. **KA-Agent 实例未注册**：
   - 所有 P0 测试返回 500 错误
   - 日志：`Internal agent 'ka-agent' instance not found`
   - `get_agent_info("ka-agent")` 返回 `exists=True`，但实例未存储

2. **空查询错误**：
   - 返回 422 Unprocessable Entity
   - 错误消息：`String should have at least 1 character, input=`
   - 用户不友好

### 修复后

1. **KA-Agent 实例注册**：
   - 实例检查：如果实例不存在，记录错误并提前返回
   - 注册验证：注册后验证实例是否成功存储
   - 诊断日志：详细的注册过程日志，便于追踪问题
   - 预期：KA-Agent 实例成功注册，不再出现 500 错误

2. **空查询错误处理**：
   - 检测空查询：自动识别空查询错误
   - 友好消息：使用 KA-Agent 错误处理器生成友好消息
   - 正确状态码：返回 400 而非 422
   - 预期：空查询返回友好的错误消息，包含建议操作

---

## 验证步骤

### 1. 重启 FastAPI（无 reload 模式）

```bash
./scripts/start_services.sh api
```

### 2. 检查日志

```bash
tail -f logs/agent.log | grep -E "KA-Agent|ka-agent|register|instance"
```

**预期日志输出**：
```
✅ KA-Agent instance found: KnowledgeArchitectAgent, agent_id=ka-agent
Registering Knowledge Architect Agent (v1.5) (ka-agent) with instance: KnowledgeArchitectAgent
✅ Stored agent instance for internal agent 'ka-agent': KnowledgeArchitectAgent
✅ Knowledge Architect Agent (v1.5) (ka-agent) instance stored successfully: KnowledgeArchitectAgent
```

### 3. 运行 P0 测试

使用测试脚本运行 P0 测试用例：

**预期结果**：
- ✅ KA-TEST-001: 不再返回 500 错误
- ✅ KA-TEST-005: 不再返回 500 错误
- ✅ KA-TEST-006: 不再返回 500 错误
- ✅ KA-TEST-016: 返回友好错误消息（400），而非 422
- ✅ KA-TEST-019: 不再返回 500 错误

### 4. 验证实例注册

```python
from agents.services.registry.registry import get_agent_registry

registry = get_agent_registry()
ka_agent_instance = registry.get_agent("ka-agent")
assert ka_agent_instance is not None, "KA-Agent instance should be registered"
print(f"✅ KA-Agent instance registered: {type(ka_agent_instance).__name__}")
```

### 5. 测试空查询

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": ""}],
    "model_selector": {"mode": "auto"}
  }'
```

**预期响应**：
- 状态码：400（而非 422）
- 消息：包含友好的错误消息和建议操作
- 不包含技术性错误信息

---

## 相关文件

- `agents/builtin/__init__.py` - KA-Agent 注册逻辑
- `agents/services/registry/registry.py` - Agent Registry 实现
- `api/main.py` - FastAPI 异常处理器
- `agents/builtin/ka_agent/error_handler.py` - KA-Agent 错误处理器
- `docs/系统设计文档/核心组件/Agent平台/KA-Agent/KA-Agent-P0測試報告.md` - 测试报告

---

## 注意事项

1. **向后兼容**：所有修复都保持向后兼容，不影响其他 Agent 的注册
2. **日志记录**：添加了详细的诊断日志，便于追踪问题
3. **错误处理**：确保所有错误路径都有适当的日志和用户反馈
4. **测试覆盖**：修复后需要重新运行完整的 P0 测试套件

---

**修复完成时间**: 2026-01-28 12:00 UTC+8
