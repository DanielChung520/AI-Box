# 治理 API 文档

**创建日期**: 2025-12-29
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-29
**关联文档**: [SeaweedFS 使用指南](../核心组件/SeaweedFS使用指南.md)、[日志存储格式说明](../核心组件/日志存储格式说明.md)

---

## 📋 概述

本文档描述 AI-Box 系统的治理相关 API，包括版本历史、变更提案和审计日志的查询接口。所有治理数据存储在 SeaweedFS 中（Append-Only 模式）。

---

## 🔐 认证要求

所有治理 API 都需要用户认证，使用 JWT Token：

```http
Authorization: Bearer <your-jwt-token>
```

---

## 📝 版本历史 API

### 获取版本历史

获取指定资源的版本历史记录。

**端点**: `GET /api/v1/governance/versions/{resource_type}/{resource_id}`

**路径参数**:

- `resource_type` (string, required): 资源类型（如 `ontologies`, `configs`）
- `resource_id` (string, required): 资源 ID

**查询参数**:

- `limit` (integer, optional): 返回数量限制（默认 100，最大 1000）

**响应示例**:

```json
{
  "success": true,
  "message": "获取版本历史成功",
  "data": [
    {
      "resource_type": "ontologies",
      "resource_id": "ontology-123",
      "version": 1,
      "change_type": "CREATE",
      "changed_by": "user-456",
      "change_summary": "Initial version of Enterprise Ontology",
      "previous_version": null,
      "current_version": {
        "name": "Enterprise Ontology",
        "version": "1.0.0",
        "entity_classes": [...],
        "object_properties": [...]
      },
      "created_at": "2025-12-29T10:30:00Z"
    },
    {
      "resource_type": "ontologies",
      "resource_id": "ontology-123",
      "version": 2,
      "change_type": "UPDATE",
      "changed_by": "user-789",
      "change_summary": "Added new entity class",
      "previous_version": {...},
      "current_version": {...},
      "created_at": "2025-12-29T11:00:00Z"
    }
  ]
}
```

**状态码**:

- `200 OK`: 成功
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 获取特定版本

获取指定资源的特定版本记录。

**端点**: `GET /api/v1/governance/versions/{resource_type}/{resource_id}/{version}`

**路径参数**:

- `resource_type` (string, required): 资源类型
- `resource_id` (string, required): 资源 ID
- `version` (integer, required): 版本号（从 1 开始）

**响应示例**:

```json
{
  "success": true,
  "message": "获取版本详情成功",
  "data": {
    "resource_type": "ontologies",
    "resource_id": "ontology-123",
    "version": 1,
    "change_type": "CREATE",
    "changed_by": "user-456",
    "change_summary": "Initial version of Enterprise Ontology",
    "previous_version": null,
    "current_version": {...},
    "created_at": "2025-12-29T10:30:00Z"
  }
}
```

**状态码**:

- `200 OK`: 成功
- `404 Not Found`: 版本不存在
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

---

## 📋 变更提案 API

### 创建变更提案

创建一个新的变更提案。

**端点**: `POST /api/v1/governance/proposals`

**请求体**:

```json
{
  "proposal_type": "config",
  "resource_id": "tenant-456",
  "proposal_data": {
    "scope": "genai.policy",
    "config_data": {
      "allowed_providers": ["openai", "anthropic"],
      "allowed_models": {...}
    }
  },
  "approval_required": true
}
```

**请求字段**:

- `proposal_type` (string, required): 提案类型（如 `config`, `ontology`）
- `resource_id` (string, optional): 资源 ID（全局提案为 null）
- `proposal_data` (object, required): 提案数据（JSON 对象）
- `approval_required` (boolean, optional): 是否需要审批（默认 true）

**响应示例**:

```json
{
  "success": true,
  "message": "变更提案创建成功",
  "data": {
    "proposal_id": "proposal-789"
  }
}
```

**状态码**:

- `201 Created`: 创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 获取提案详情

获取指定提案的详细信息。

**端点**: `GET /api/v1/governance/proposals/{proposal_id}`

**路径参数**:

- `proposal_id` (string, required): 提案 ID

**响应示例**:

```json
{
  "success": true,
  "message": "获取提案详情成功",
  "data": {
    "proposal_id": "proposal-789",
    "proposal_type": "config",
    "resource_id": "tenant-456",
    "proposed_by": "user-123",
    "status": "PENDING",
    "proposal_data": {...},
    "approval_required": true,
    "created_at": "2025-12-29T10:30:00Z",
    "updated_at": "2025-12-29T10:30:00Z",
    "approved_by": null,
    "approved_at": null,
    "rejected_by": null,
    "rejected_at": null,
    "rejection_reason": null
  }
}
```

**状态码**:

- `200 OK`: 成功
- `404 Not Found`: 提案不存在
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 审批提案

审批一个变更提案。审批通过后，提案内容将应用到 ArangoDB（Active State）。

**端点**: `POST /api/v1/governance/proposals/{proposal_id}/approve`

**路径参数**:

- `proposal_id` (string, required): 提案 ID

**响应示例**:

```json
{
  "success": true,
  "message": "提案审批成功"
}
```

**状态码**:

- `200 OK`: 审批成功
- `404 Not Found`: 提案不存在
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 拒绝提案

拒绝一个变更提案。

**端点**: `POST /api/v1/governance/proposals/{proposal_id}/reject`

**路径参数**:

- `proposal_id` (string, required): 提案 ID

**请求体**:

```json
{
  "reason": "不符合安全策略要求"
}
```

**请求字段**:

- `reason` (string, required): 拒绝原因

**响应示例**:

```json
{
  "success": true,
  "message": "提案拒绝成功"
}
```

**状态码**:

- `200 OK`: 拒绝成功
- `404 Not Found`: 提案不存在
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

### 列出提案

列出提案列表，支持按类型、资源 ID 和状态过滤。

**端点**: `GET /api/v1/governance/proposals`

**查询参数**:

- `proposal_type` (string, optional): 提案类型（如 `config`, `ontology`）
- `resource_id` (string, optional): 资源 ID
- `status` (string, optional): 提案状态（`PENDING`, `APPROVED`, `REJECTED`）
- `limit` (integer, optional): 返回数量限制（默认 100，最大 1000）

**响应示例**:

```json
{
  "success": true,
  "message": "获取提案列表成功",
  "data": [
    {
      "proposal_id": "proposal-789",
      "proposal_type": "config",
      "resource_id": "tenant-456",
      "proposed_by": "user-123",
      "status": "PENDING",
      "created_at": "2025-12-29T10:30:00Z",
      "updated_at": "2025-12-29T10:30:00Z"
    }
  ]
}
```

**状态码**:

- `200 OK`: 成功
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

---

## 📊 审计日志 API

### 获取审计日志

查询审计日志记录。审计日志存储在 SeaweedFS 中，按时间分片存储（JSON Lines 格式）。

**端点**: `GET /api/v1/governance/audit-logs`

**查询参数**:

- `user_id` (string, optional): 用户 ID（仅管理员可用）
- `action` (string, optional): 操作类型（如 `CREATE`, `UPDATE`, `DELETE`, `READ`）
- `resource_type` (string, optional): 资源类型（如 `ontology`, `config`, `file`）
- `resource_id` (string, optional): 资源 ID
- `start_time` (datetime, optional): 开始时间（ISO 8601 格式）
- `end_time` (datetime, optional): 结束时间（ISO 8601 格式）
- `limit` (integer, optional): 返回数量限制（默认 100，最大 1000）

**响应示例**:

```json
{
  "success": true,
  "message": "获取审计日志成功",
  "data": [
    {
      "id": "audit-log-uuid",
      "user_id": "user-123",
      "action": "CREATE",
      "resource_type": "ontology",
      "resource_id": "ontology-456",
      "timestamp": "2025-12-29T10:30:00Z",
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0...",
      "details": {
        "ontology_name": "Enterprise Ontology",
        "version": "1.0.0"
      }
    }
  ]
}
```

**状态码**:

- `200 OK`: 成功
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 权限不足（非管理员用户只能查询自己的日志）
- `500 Internal Server Error`: 服务器错误

**注意**: 非管理员用户只能查询自己的审计日志。管理员用户可以查询所有用户的日志。

---

## 📈 治理报告 API

### 获取治理报告

生成 AI 治理报告，包括操作统计、变更提案统计等。

**端点**: `GET /api/v1/governance/report`

**查询参数**:

- `start_time` (datetime, optional): 开始时间（ISO 8601 格式）
- `end_time` (datetime, optional): 结束时间（ISO 8601 格式）
- `user_id` (string, optional): 用户 ID（仅管理员可用）

**响应示例**:

```json
{
  "success": true,
  "message": "AI治理报告生成成功",
  "data": {
    "period": {
      "start_time": "2025-12-01T00:00:00Z",
      "end_time": "2025-12-29T23:59:59Z"
    },
    "statistics": {
      "total_operations": 1000,
      "create_operations": 300,
      "update_operations": 500,
      "delete_operations": 50,
      "read_operations": 150
    },
    "proposals": {
      "total": 50,
      "pending": 10,
      "approved": 35,
      "rejected": 5
    },
    "version_history": {
      "total_versions": 200,
      "ontology_versions": 100,
      "config_versions": 100
    }
  }
}
```

**状态码**:

- `200 OK`: 成功
- `401 Unauthorized`: 未认证
- `500 Internal Server Error`: 服务器错误

---

## 🔍 错误码说明

| 状态码 | 说明 | 解决方案 |
|--------|------|---------|
| `200 OK` | 请求成功 | - |
| `201 Created` | 资源创建成功 | - |
| `400 Bad Request` | 请求参数错误 | 检查请求参数格式和必填字段 |
| `401 Unauthorized` | 未认证 | 提供有效的 JWT Token |
| `403 Forbidden` | 权限不足 | 确认用户权限或联系管理员 |
| `404 Not Found` | 资源不存在 | 检查资源 ID 是否正确 |
| `500 Internal Server Error` | 服务器错误 | 查看服务器日志或联系技术支持 |

---

## 📚 相关文档

- [SeaweedFS 使用指南](../核心组件/SeaweedFS使用指南.md) - SeaweedFS 使用指南
- [日志存储格式说明](../核心组件/日志存储格式说明.md) - 日志存储格式详细说明
- [资料架构建议报告](../資料架构建议报告.md) - 架构演进建议

---

**最后更新日期**: 2025-12-29
