<!-- 7f418f24-d785-480c-8341-b3a5019d0e33 5eacdaf7-3063-47d6-aa22-a1bf49e17e00 -->
# 阶段 2：Registry 核心功能扩展 - 详细任务计划

## 目标

更新 Agent Registry，支持内部 Agent 实例存储和智能路由功能，实现统一接口但根据 `is_internal` 标志智能返回实例或 Client。

## 重要原则

**在开始每个任务前，必须先分析现有代码，避免重复创建或冲突。**

---

## 任务 2.1：扩展 AgentRegistry 类，添加实例存储

### 前置分析

- 检查文件：`agents/services/registry/registry.py`
- 现有结构：`self._agents: Dict[str, AgentRegistryInfo] = {}`
- 需要添加：`self._agent_instances: Dict[str, AgentServiceProtocol] = {}`

### 具体步骤

1. **分析现有代码**

- 读取 `agents/services/registry/registry.py` 第 28-40 行
- 确认 `__init__` 方法的当前实现
- 检查是否有其他地方直接访问 `_agents`

2. **添加实例存储字典**

- 在 `__init__` 方法中添加 `self._agent_instances: Dict[str, AgentServiceProtocol] = {}`
- 添加类型注解导入（如果缺失）

### 文件修改

- `agents/services/registry/registry.py` (第 31-40 行，扩展 `__init__` 方法)

### 验收标准

- [ ] `AgentRegistry` 类包含 `_agent_instances` 字典
- [ ] 类型注解正确
- [ ] 现有代码仍能正常工作

---

## 任务 2.2：更新 register_agent() 方法，支持实例参数

### 前置分析

- 检查文件：`agents/services/registry/registry.py`
- 现有方法：`register_agent(self, request: AgentRegistrationRequest) -> bool`
- 需要添加：`instance: Optional[AgentServiceProtocol] = None` 参数

### 具体步骤

1. **分析现有代码**

- 读取 `agents/services/registry/registry.py` 第 42-100 行
- 检查所有调用 `register_agent()` 的地方
- 确认是否需要更新调用方

2. **更新方法签名**

- 添加 `instance: Optional[AgentServiceProtocol] = None` 参数
- 更新文档字符串

3. **实现实例存储逻辑**

- 如果是内部 Agent（`request.endpoints.is_internal == True`）且提供了 `instance`
- 将实例存储到 `_agent_instances` 字典中
- 如果是外部 Agent，验证认证配置（调用认证服务）

4. **更新现有 Agent 逻辑**

- 在更新现有 Agent 时，如果提供了新实例，更新 `_agent_instances`

### 文件修改

- `agents/services/registry/registry.py` (第 42-100 行，更新 `register_agent` 方法)

### 验收标准

- [ ] `register_agent()` 方法支持 `instance` 参数
- [ ] 内部 Agent 实例正确存储到 `_agent_instances`
- [ ] 外部 Agent 认证配置验证逻辑正确
- [ ] 现有调用代码仍能正常工作（向后兼容）

---

## 任务 2.3：重构 get_agent() 方法，实现智能路由

### 前置分析

- 检查文件：`agents/services/registry/registry.py`
- 现有方法：`get_agent(self, agent_id: str) -> Optional[AgentRegistryInfo]`
- 需要修改：返回类型改为 `Optional[AgentServiceProtocol]`，智能返回实例或 Client

### 具体步骤

1. **分析现有代码**

- 读取 `agents/services/registry/registry.py` 第 134-144 行
- 搜索所有调用 `get_agent()` 的地方
- 确认返回类型变更的影响

2. **重构方法实现**

- 修改返回类型为 `Optional[AgentServiceProtocol]`
- 获取 `AgentRegistryInfo`
- 如果是内部 Agent，从 `_agent_instances` 返回实例
- 如果是外部 Agent，调用 `get_agent_client()` 返回 Client

3. **添加新方法 get_agent_info()**

- 创建 `get_agent_info()` 方法，返回 `Optional[AgentRegistryInfo]`
- 用于需要获取 Agent 信息的场景

4. **更新文档字符串**

- 说明智能路由逻辑
- 提供使用示例

### 文件修改

- `agents/services/registry/registry.py` (第 134-144 行，重构 `get_agent` 方法)
- `agents/services/registry/registry.py` (添加 `get_agent_info` 方法)

### 验收标准

- [ ] `get_agent()` 方法返回 `AgentServiceProtocol`
- [ ] 内部 Agent 返回实例（从 `_agent_instances`）
- [ ] 外部 Agent 返回 Client（通过 `get_agent_client()`）
- [ ] `get_agent_info()` 方法可用
- [ ] 现有调用代码更新（如果需要）

---

## 任务 2.4：更新 get_agent_client() 方法，传递认证信息

### 前置分析

- 检查文件：`agents/services/registry/registry.py`
- 现有方法：`get_agent_client(self, agent_id: str) -> Optional[AgentServiceProtocol]`
- 需要修改：传递认证配置参数给 Factory

### 具体步骤

1. **分析现有代码**

- 读取 `agents/services/registry/registry.py` 第 146-177 行
- 确认 Factory.create() 的参数结构（已在阶段1扩展）

2. **更新方法实现**

- 从 `agent_info.permissions` 获取认证配置
- 传递 `api_key`, `server_certificate`, `ip_whitelist`, `server_fingerprint` 给 Factory
- 确保只处理外部 Agent（内部 Agent 应该通过 `get_agent()` 获取实例）

3. **添加验证逻辑**

- 检查 Agent 是否为外部 Agent
- 如果是内部 Agent，记录警告并返回 None

### 文件修改

- `agents/services/registry/registry.py` (第 146-177 行，更新 `get_agent_client` 方法)

### 验收标准

- [ ] `get_agent_client()` 传递认证配置给 Factory
- [ ] 外部 Agent 正确创建带认证的 Client
- [ ] 内部 Agent 调用时返回 None 或记录警告

---

## 任务 2.5：更新 unregister_agent() 方法，清理实例

### 前置分析

- 检查文件：`agents/services/registry/registry.py`
- 现有方法：`unregister_agent(self, agent_id: str) -> bool`
- 需要修改：同时清理 `_agent_instances` 中的实例

### 具体步骤

1. **分析现有代码**

- 读取 `agents/services/registry/registry.py` 第 102-132 行
- 确认清理逻辑

2. **更新方法实现**

- 在标记 Agent 为离线后，从 `_agent_instances` 中删除实例
- 如果实例存在，可以调用 `close()` 方法（如果支持）

3. **添加错误处理**

- 确保清理失败不影响主流程

### 文件修改

- `agents/services/registry/registry.py` (第 102-132 行，更新 `unregister_agent` 方法)

### 验收标准

- [ ] `unregister_agent()` 同时清理 `_agent_instances`
- [ ] 实例正确清理
- [ ] 错误处理完善

---

## 任务 2.6：更新调用方代码

### 前置分析

- 检查所有调用 `get_agent()` 的地方
- 确认是否需要更新以适配新的返回类型

### 具体步骤

1. **搜索调用位置**

- `agents/services/registry/discovery.py`
- `agents/services/registry/task_executor.py`
- `agents/services/registry/auto_registration.py`
- `api/routers/agent_registry.py`
- 其他可能的位置

2. **更新调用代码**

- 如果调用方需要 `AgentRegistryInfo`，改为调用 `get_agent_info()`
- 如果调用方需要 `AgentServiceProtocol`，使用 `get_agent()`
- 确保类型匹配

### 文件修改

- `agents/services/registry/discovery.py` (如果使用 `get_agent()`)
- `agents/services/registry/task_executor.py` (如果使用 `get_agent()`)
- `api/routers/agent_registry.py` (如果使用 `get_agent()`)

### 验收标准

- [ ] 所有调用方代码更新完成
- [ ] 类型检查通过
- [ ] 功能正常

---

## 测试计划

### 单元测试

- [ ] `register_agent()` 内部 Agent 实例存储测试
- [ ] `register_agent()` 外部 Agent 认证验证测试
- [ ] `get_agent()` 内部 Agent 返回实例测试
- [ ] `get_agent()` 外部 Agent 返回 Client 测试
- [ ] `get_agent_info()` 方法测试
- [ ] `unregister_agent()` 实例清理测试

### 集成测试

- [ ] 内部 Agent 注册和获取流程测试
- [ ] 外部 Agent 注册和获取流程测试
- [ ] 混合场景测试（内部 + 外部 Agent）

### 类型检查

- [ ] 运行 `mypy agents/services/registry/registry.py`
- [ ] 运行 `mypy agents/services/registry/discovery.py`
- [ ] 运行 `mypy agents/services/registry/task_executor.py`

---

## 预计时间

- 任务 2.1：0.5 天
- 任务 2.2：1.5 天
- 任务 2.3：2 天
- 任务 2.4：1 天
- 任务 2.5：0.5 天
- 任务 2.6：1.5 天
- 测试：1 天

**总计：8 天（约 1.5 周）**

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 返回类型变更影响现有代码 | 高 | 提供 `get_agent_info()` 方法，保持向后兼容 |
| 实例生命周期管理 | 中 | 实现正确的清理逻辑，添加错误处理 |
| 认证配置传递错误 | 中 | 充分测试，添加验证逻辑 |

---

## 依赖关系

- 阶段1：模型扩展和认证服务模块（已完成）
- 阶段4：核心 Agent 迁移（依赖阶段2的智能路由功能）

### To-dos

- [ ] 分析现有系统架构，识别需要迁移的组件
- [ ] 制定分阶段迁移计划文档
- [ ] 创建 Git 重构分支：refactoring/directory-restructure
- [ ] 备份测试代码：创建 tests_backup/ 目录，备份所有测试文件和 pytest.ini
- [ ] 创建新目录结构：按照 DIRECTORY_STRUCTURE.md 创建所有目标目录
- [ ] 创建迁移日志文件：创建 docs/REFACTORING_LOG.md 并添加模板
- [ ] 创建 __init__.py 文件：为所有新创建的 Python 包目录添加 __init__.py
- [ ] 验证和提交：验证所有检查点，提交更改并创建阶段 0 完成标签
- [ ] 任务2.1：扩展 AgentRegistry 类，添加 _agent_instances 实例存储字典
- [ ] 任务2.2：更新 register_agent() 方法，支持 instance 参数和实例存储
- [ ] 任务2.3：重构 get_agent() 方法，实现智能路由（返回实例或 Client）
- [ ] 任务2.4：更新 get_agent_client() 方法，传递认证配置参数
- [ ] 任务2.5：更新 unregister_agent() 方法，清理实例存储
- [ ] 任务2.6：更新所有调用方代码，适配新的返回类型
- [ ] 阶段2测试：单元测试、集成测试、类型检查
