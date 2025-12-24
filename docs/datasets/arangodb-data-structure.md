# ArangoDB 數據結構文檔

**創建日期**: 2025-12-18 20:49:06 (UTC+8)
**創建人**: Daniel Chung
**最後修改日期**: 2025-12-18 20:49:06 (UTC+8)

---

## 概述

本文檔詳細說明 AI-Box 項目中 ArangoDB 數據庫的所有 Collections 及其數據結構。ArangoDB 作為項目的統一數據存儲系統，替代了原有的文件系統存儲（Ontology、Config）和部分 Redis 存儲（文件上傳狀態）。

---

## Collections 總覽

### Document Collections（文檔集合）共 15 個

| # | Collection 名稱 | 用途 | 服務類 | 多租戶 | TTL |
|---|----------------|------|--------|--------|-----|
| 1 | `ontologies` | Ontology 定義存儲 | `OntologyStoreService` | ✅ | - |
| 2 | `system_configs` | 系統級配置 | `ConfigStoreService` | ❌ | - |
| 3 | `tenant_configs` | 租戶級配置 | `ConfigStoreService` | ✅ | - |
| 4 | `user_configs` | 用戶級配置 | `ConfigStoreService` | ✅ | - |
| 5 | `audit_logs` | 審計日誌 | `AuditLogService` | ✅ | - |
| 6 | `upload_progress` | 文件上傳進度 | `UploadStatusService` | ✅ | 1小時 |
| 7 | `processing_status` | 文件處理狀態 | `UploadStatusService` | ✅ | 24小時 |
| 8 | `file_metadata` | 文件元數據 | `FileMetadataService` | ✅ | - |
| 9 | `folder_metadata` | 文件夾元數據 | `TaskWorkspaceService` | ✅ | - |
| 10 | `genai_tenant_policies` | GenAI 租戶策略 | `GenAITenantPolicyService` | ✅ | - |
| 11 | `genai_tenant_secrets` | GenAI 租戶密鑰（加密） | `GenAITenantPolicyService` | ✅ | - |
| 12 | `genai_user_llm_secrets` | GenAI 用戶 LLM 密鑰（加密） | `GenAIUserLLMSecretService` | ✅ | - |
| 13 | `model_usage` | 模型使用記錄 | `ModelUsageService` | ✅ | - |
| 14 | `operation_logs` | 操作日誌 | `OperationLogService` | ✅ | - |
| 15 | `user_tasks` | 用戶任務 | `UserTaskService` | ✅ | - |

### Graph Collections（圖集合）共 2 個

| # | Collection 名稱 | 用途 | 類型 | 說明 |
|---|----------------|------|------|------|
| 16 | `entities` | 知識圖譜實體 | Edge/Vertex | 動態創建，按文件ID組織 |
| 17 | `relations` | 知識圖譜關係 | Edge | 動態創建，按文件ID組織 |

---

## 詳細數據結構

### 1. ontologies

**用途**: 存儲 Ontology 定義（base/domain/major 三種類型）

**服務**: `services/api/services/ontology_store_service.py`

**文檔結構**:

```json
{
  "_key": "base-ontology-name-1.0.0",
  "tenant_id": "tenant_123" | null,
  "type": "base" | "domain" | "major",
  "name": "ontology-name",
  "version": "1.0.0",
  "default_version": true | false,
  "ontology_name": "Full Ontology Name",
  "description": "Description text",
  "author": "Author Name",
  "last_modified": "2025-12-18T12:00:00Z",
  "inherits_from": ["parent-ontology-1", "parent-ontology-2"],
  "compatible_domains": ["domain-1", "domain-2"],
  "tags": ["tag1", "tag2"],
  "use_cases": ["use-case-1"],
  "entity_classes": [
    {
      "name": "EntityName",
      "description": "Entity description",
      "base_class": "BaseClass",
      "role": "5W1H role"
    }
  ],
  "object_properties": [
    {
      "name": "relationName",
      "description": "Relation description",
      "domain": ["EntityType1"],
      "range": ["EntityType2"]
    }
  ],
  "metadata": {},
  "is_active": true,
  "data_classification": "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED" | null,
  "sensitivity_labels": ["PII", "PHI"] | null,
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z",
  "created_by": "user_id",
  "updated_by": "user_id"
}
```

**索引**:

- `idx_ontologies_tenant_type_name`: `["tenant_id", "type", "name"]`
- `idx_ontologies_tenant_type_name_version`: `["tenant_id", "type", "name", "version"]`
- `idx_ontologies_type_name_default`: `["type", "name", "default_version"]`
- `idx_ontologies_is_active`: `["is_active"]`

---

### 2. system_configs / tenant_configs / user_configs

**用途**: 存儲系統/租戶/用戶級配置（層級合併：System → Tenant → User）

**服務**: `services/api/services/config_store_service.py`

**文檔結構**:

```json
{
  "_key": "scope" | "tenant_id_scope" | "tenant_id_user_id_scope",
  "tenant_id": null | "tenant_123",
  "user_id": null | "user_456",
  "scope": "genai.policy" | "genai.model_registry",
  "sub_scope": "sub_scope_name" | null,
  "is_active": true,
  "config_data": {
    "key1": "value1",
    "key2": {"nested": "object"}
  },
  "metadata": {
    "description": "Config description",
    "version": "1.0"
  },
  "data_classification": "PUBLIC" | "INTERNAL" | "CONFIDENTIAL" | "RESTRICTED" | null,
  "sensitivity_labels": ["PII", "PHI"] | null,
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z",
  "created_by": "user_id",
  "updated_by": "user_id"
}
```

**索引**:

- `system_configs`: `idx_system_configs_scope_active` → `["scope", "is_active"]`
- `tenant_configs`: `idx_tenant_configs_tenant_scope_active` → `["tenant_id", "scope", "is_active"]`
- `user_configs`: `idx_user_configs_tenant_user_scope_active` → `["tenant_id", "user_id", "scope", "is_active"]`

---

### 3. audit_logs

**用途**: 審計日誌追蹤（WBS-4.1: AI 治理與合規）

**服務**: `services/api/services/audit_log_service.py`

**文檔結構**:

```json
{
  "_key": "uuid-generated-id",
  "user_id": "user_123",
  "action": "ontology_create" | "config_update" | "file_delete" | ...,
  "resource_type": "ontology" | "config" | "file" | "task",
  "resource_id": "resource_id_123",
  "timestamp": "2025-12-18T12:00:00Z",
  "ip_address": "192.168.1.1",
  "user_agent": "Mozilla/5.0...",
  "details": {
    "additional": "information"
  }
}
```

**索引**:

- `["user_id"]`
- `["action"]`
- `["timestamp"]`
- `["resource_type", "resource_id"]`

---

### 4. upload_progress

**用途**: 文件上傳進度追蹤（WBS-3.7: 文件上傳流程重構）

**服務**: `services/api/services/upload_status_service.py`

**文檔結構**:

```json
{
  "_key": "file_id_123",
  "file_id": "file_id_123",
  "status": "uploading" | "completed" | "failed",
  "progress": 75,
  "message": "Uploading...",
  "file_size": 1024000,
  "uploaded_bytes": 768000,
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:05:00Z"
}
```

**索引**:

- `["file_id"]`
- `["status"]`
- TTL: `["updated_at"]` (expireAfter: 3600 秒 = 1小時)

---

### 5. processing_status

**用途**: 文件處理狀態追蹤（WBS-3.7）

**服務**: `services/api/services/upload_status_service.py`

**文檔結構**:

```json
{
  "_key": "file_id_123",
  "file_id": "file_id_123",
  "overall_status": "processing" | "completed" | "failed",
  "overall_progress": 60,
  "message": "Processing chunks...",
  "chunking": {
    "status": "completed",
    "progress": 100,
    "message": "Chunking completed"
  },
  "vectorization": {
    "status": "processing",
    "progress": 50,
    "message": "Vectorizing..."
  },
  "storage": {
    "status": "pending",
    "progress": 0,
    "message": "Waiting..."
  },
  "kg_extraction": {
    "status": "pending",
    "progress": 0,
    "message": "Waiting..."
  },
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:10:00Z"
}
```

**索引**:

- `["file_id"]`
- `["overall_status"]`
- TTL: `["updated_at"]` (expireAfter: 86400 秒 = 24小時)

---

### 6. file_metadata

**用途**: 文件元數據存儲

**服務**: `services/api/services/file_metadata_service.py`

**文檔結構**:

```json
{
  "_key": "file_id_123",
  "file_id": "file_id_123",
  "filename": "document.pdf",
  "file_type": "application/pdf",
  "file_size": 1024000,
  "user_id": "user_123",
  "task_id": "task_456",
  "folder_id": "folder_789",
  "storage_path": "/path/to/file",
  "tags": ["tag1", "tag2"],
  "description": "File description",
  "custom_metadata": {},
  "status": "uploaded" | "processing" | "completed",
  "processing_status": "chunking" | "vectorizing" | "completed",
  "chunk_count": 100,
  "vector_count": 100,
  "kg_status": "pending" | "extracting" | "completed",
  "upload_time": "2025-12-18T12:00:00Z",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z"
}
```

**索引**:

- `["file_id"]`
- `["filename"]`
- `["file_type"]`
- `["user_id"]`
- `["task_id"]`
- `["folder_id"]`
- `["status"]`
- `["upload_time"]`

---

### 7. folder_metadata

**用途**: 文件夾元數據存儲

**服務**: `services/api/services/task_workspace_service.py`

**文檔結構**:

```json
{
  "_key": "folder_id_123",
  "folder_id": "folder_id_123",
  "folder_name": "任務工作區",
  "parent_folder_id": "parent_folder_id" | null,
  "user_id": "user_123",
  "task_id": "task_456",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z"
}
```

**索引**: 根據查詢需求創建

---

### 8. genai_tenant_policies

**用途**: GenAI 租戶策略（非敏感）

**服務**: `services/api/services/genai_tenant_policy_service.py`

**文檔結構**:

```json
{
  "_key": "tenant_123",
  "tenant_id": "tenant_123",
  "allowed_providers": ["openai", "anthropic"],
  "allowed_models": {
    "openai": ["gpt-4", "gpt-4o"],
    "anthropic": ["claude-3-opus"]
  },
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z"
}
```

---

### 9. genai_tenant_secrets

**用途**: GenAI 租戶密鑰（敏感，加密存儲）

**服務**: `services/api/services/genai_tenant_policy_service.py`

**文檔結構**:

```json
{
  "_key": "tenant_123_openai",
  "tenant_id": "tenant_123",
  "provider": "openai",
  "encrypted_api_key": "encrypted_string",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z"
}
```

**注意**: 必須使用 `GenAISecretEncryptionService` 加密

---

### 10. genai_user_llm_secrets

**用途**: GenAI 用戶 LLM API Key（敏感，加密存儲）

**服務**: `services/api/services/genai_user_llm_secret_service.py`

**文檔結構**:

```json
{
  "_key": "tenant_123_user_456_openai",
  "tenant_id": "tenant_123",
  "user_id": "user_456",
  "provider": "openai",
  "encrypted_api_key": "encrypted_string",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z"
}
```

**注意**: 必須使用 `GenAISecretEncryptionService` 加密

---

### 11. model_usage

**用途**: 模型使用記錄和統計

**服務**: `services/api/services/model_usage_service.py`

**文檔結構**:

```json
{
  "_key": "uuid-generated-id",
  "model_name": "gpt-4",
  "provider": "openai",
  "user_id": "user_123",
  "file_id": "file_id_123",
  "request_tokens": 1000,
  "response_tokens": 500,
  "total_tokens": 1500,
  "timestamp": "2025-12-18T12:00:00Z",
  "metadata": {
    "additional": "info"
  }
}
```

**索引**:

- `["model_name"]`
- `["user_id"]`
- `["file_id"]`
- `["timestamp"]`

---

### 12. operation_logs

**用途**: 操作日誌記錄

**服務**: `services/api/services/operation_log_service.py`

**文檔結構**:

```json
{
  "_key": "uuid-generated-id",
  "user_id": "user_123",
  "resource_id": "resource_id_123",
  "resource_type": "task" | "document",
  "resource_name": "Resource Name",
  "operation_type": "create" | "update" | "archive" | "delete",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z",
  "archived_at": "2025-12-18T12:00:00Z" | null,
  "deleted_at": "2025-12-18T12:00:00Z" | null
}
```

---

### 13. user_tasks

**用途**: 用戶任務管理

**服務**: `services/api/services/user_task_service.py`

**文檔結構**:

```json
{
  "_key": "task_id_123",
  "task_id": "task_id_123",
  "user_id": "user_123",
  "task_name": "Task Name",
  "status": "pending" | "running" | "completed" | "failed",
  "created_at": "2025-12-18T12:00:00Z",
  "updated_at": "2025-12-18T12:00:00Z",
  "metadata": {
    "additional": "task info"
  }
}
```

**索引**:

- `["task_id"]`
- `["user_id"]`
- `["status"]`
- `["created_at"]`

---

### 14. entities / relations（知識圖譜）

**用途**: 知識圖譜實體和關係存儲

**命名**: 可使用 `entities_{file_id}` 和 `relations_{file_id}` 或統一的 `entities` / `relations`

**entities 文檔結構**:

```json
{
  "_key": "entity_id_123",
  "name": "Entity Name",
  "type": "EntityType",
  "file_id": "file_id_123",
  "metadata": {
    "additional": "entity info"
  }
}
```

**relations 文檔結構**:

```json
{
  "_key": "relation_id_123",
  "_from": "entities/entity_id_1",
  "_to": "entities/entity_id_2",
  "type": "RelationType",
  "file_id": "file_id_123",
  "metadata": {
    "additional": "relation info"
  }
}
```

---

## 數據存儲原則

### 1. 多租戶隔離

- 所有租戶級數據必須包含 `tenant_id` 字段
- 系統級數據使用 `tenant_id: null`
- 所有查詢必須過濾 `tenant_id`

### 2. 軟刪除

- 重要數據使用 `is_active: false` 標記為已刪除
- 臨時數據可以使用物理刪除
- TTL 索引自動清理過期數據

### 3. 數據分類

- 支持數據分類級別（PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED）
- 支持敏感性標籤（PII / PHI / FINANCIAL / IP / CUSTOMER / PROPRIETARY）

### 4. 加密存儲

- 敏感數據（API Keys）必須加密後存儲
- 使用 `GenAISecretEncryptionService` 進行加密

### 5. 時間戳

- 所有文檔必須包含 `created_at` 和 `updated_at` 字段
- 使用 ISO 8601 格式字符串

---

## Schema 管理

### Schema 創建腳本

位置: `scripts/migration/create_schema.py`

運行: `python scripts/migration/create_schema.py`

### 數據遷移腳本

- `scripts/migration/migrate_ontologies.py`: Ontology 數據遷移
- `scripts/migration/migrate_configs.py`: Config 數據遷移

---

## 相關規範文檔

- 詳細開發規範: `.cursor/rules/develop-rule.mdc`（ArangoDB 數據存儲規範章節）
- Schema 腳本: `scripts/migration/create_schema.py`
- Store Services: `services/api/services/*_store_service.py`
- 數據模型: `services/api/models/`

---

**最後更新**: 2025-12-18 20:49:06 (UTC+8)
