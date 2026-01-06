# SeaweedFS 使用指南

**创建日期**: 2025-12-29
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-29
**关联文档**: [存储架构](./存储架构.md)、[资料架构建议报告](../資料架构建议报告.md)

---

## 📋 概述

本文档提供 AI-Box 系统中 SeaweedFS 分布式文件系统的使用指南，包括双服务部署架构、Buckets 配置、S3 API 使用示例和常见问题解答。

---

## 🏗️ SeaweedFS 架构说明

### 双服务部署架构

AI-Box 系统使用 **SeaweedFS 双服务部署架构**，分别为 AI-Box 和 DataLake 项目提供独立的存储服务：

1. **AI-Box SeaweedFS 服务**：存放 AI-Box 项目内的非结构化数据
2. **DataLake SeaweedFS 服务**：存放 DataLake 项目的文件备份数据

**架构优势**：

- ✅ **职责分离**：AI-Box 和 DataLake 各自管理自己的存储
- ✅ **独立扩展**：两个服务可以根据各自需求独立扩展
- ✅ **数据隔离**：避免两个项目之间的数据混杂
- ✅ **灵活部署**：可以根据实际需求选择不同的部署策略

### 组件架构

SeaweedFS 采用 Master-Volume-Filer 三层架构：

- **Master 节点**：管理元数据和 Volume 节点（高可用，3 副本）
- **Volume 节点**：存储实际数据（存储节点，3 副本）
- **Filer 节点**：提供文件系统接口和 S3 API（文件系统接口，2 副本）

---

## 🔧 Buckets 配置说明

### AI-Box SeaweedFS 服务 Buckets

| Bucket 名称 | 用途 | 存储内容 |
|------------|------|---------|
| `bucket-governance-logs` | 治理相关日志 | 审计日志、系统日志（JSON Lines 格式） |
| `bucket-version-history` | 版本历史记录 | 配置和 Ontology 的历史版本（JSON 格式） |
| `bucket-change-proposals` | 变更提案记录 | 变更提案记录（JSON 格式） |
| `bucket-datalake-dictionary` | DataLake dictionary 定义 | Data Agent 保存的 DataLake dictionary 定义 |
| `bucket-datalake-schema` | DataLake schema 定义 | Data Agent 保存的 DataLake schema 定义 |
| `bucket-ai-box-assets` | AI-Box 项目其他非结构化数据 | 用户上传文件、Agent 产出文件等 |

### DataLake SeaweedFS 服务 Buckets

| Bucket 名称 | 用途 | 存储内容 |
|------------|------|---------|
| `bucket-file-backups` | 文件备份数据 | 文件备份数据 |
| `bucket-datalake-assets` | DataLake 项目相关存储需求 | DataLake 项目相关的其他存储需求 |

---

## 💻 S3 API 使用示例

### 环境变量配置

```bash
# AI-Box 专案的 SeaweedFS 配置
AI_BOX_SEAWEEDFS_S3_ENDPOINT=http://seaweedfs-ai-box-filer:8333
AI_BOX_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
AI_BOX_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
AI_BOX_SEAWEEDFS_USE_SSL=false
AI_BOX_SEAWEEDFS_FILER_ENDPOINT=http://seaweedfs-ai-box-filer:8888

# DataLake 专案的 SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://seaweedfs-datalake-filer:8333
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://seaweedfs-datalake-filer:8888
```

### Python 代码示例

#### 1. 创建存储实例

```python
from storage.s3_storage import S3FileStorage, SeaweedFSService
import os

# 创建 AI-Box 服务的存储实例
storage = S3FileStorage(
    endpoint=os.getenv("AI_BOX_SEAWEEDFS_S3_ENDPOINT"),
    access_key=os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY"),
    secret_key=os.getenv("AI_BOX_SEAWEEDFS_S3_SECRET_KEY"),
    use_ssl=False,
    service_type=SeaweedFSService.AI_BOX,
)

# 或使用配置创建
from storage.file_storage import create_storage_from_config

config = {
    "storage_backend": "s3",
    "service_type": "ai_box",  # 或 "datalake"
}
storage = create_storage_from_config(config, service_type="ai_box")
```

#### 2. 文件操作

```python
# 保存文件
file_id, s3_uri = storage.save_file(
    file_content=b"file content",
    filename="test.txt",
    task_id="task-123",  # 可选
)

# 读取文件
content = storage.read_file(file_id=file_id)

# 删除文件
success = storage.delete_file(file_id=file_id)

# 检查文件是否存在
exists = storage.file_exists(file_id=file_id)
```

#### 3. 选择不同的服务

```python
# 使用 AI-Box 服务
ai_box_storage = create_storage_from_config(config, service_type="ai_box")

# 使用 DataLake 服务
datalake_storage = create_storage_from_config(config, service_type="datalake")
```

---

## 📁 文件操作 API 说明

### S3FileStorage 类方法

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `save_file()` | 保存文件到 SeaweedFS | `file_content`, `filename`, `file_id`, `task_id` | `(file_id, s3_uri)` |
| `read_file()` | 从 SeaweedFS 读取文件 | `file_id` | `bytes` 或 `None` |
| `delete_file()` | 从 SeaweedFS 删除文件 | `file_id` | `bool` |
| `file_exists()` | 检查文件是否存在 | `file_id` | `bool` |
| `get_file_path()` | 获取文件 S3 URI | `file_id` | `str` 或 `None` |

### 文件路径组织

文件在 SeaweedFS 中的路径组织方式：

- **普通文件**：`files/{file_id}`
- **任务相关文件**：`tasks/{task_id}/{file_id}`
- **治理日志**：`logs/{log_type}/{YYYY}/{MM}/{DD}.jsonl`
- **版本历史**：`versions/{resource_type}/{resource_id}/v{version}.json`
- **变更提案**：`proposals/{proposal_type}/{resource_id}/{proposal_id}.json`

---

## 🚀 部署指南

### Kubernetes 部署

SeaweedFS 服务通过 Kubernetes 部署，包括以下组件：

1. **Master 节点**：管理元数据和 Volume 节点
2. **Volume 节点**：存储实际数据
3. **Filer 节点**：提供文件系统接口和 S3 API

**部署文件位置**：

- `k8s/seaweedfs-ai-box/`：AI-Box 服务部署配置
- `k8s/seaweedfs-datalake/`：DataLake 服务部署配置

### Buckets 创建

使用 `scripts/migration/create_seaweedfs_buckets.py` 脚本创建所有必要的 Buckets：

```bash
# 创建所有 Buckets（AI-Box 和 DataLake）
python scripts/migration/create_seaweedfs_buckets.py --service all

# 只创建 AI-Box 服务的 Buckets
python scripts/migration/create_seaweedfs_buckets.py --service ai_box

# 只创建 DataLake 服务的 Buckets
python scripts/migration/create_seaweedfs_buckets.py --service datalake

# 乾運行模式（不實際創建）
python scripts/migration/create_seaweedfs_buckets.py --service all --dry-run
```

---

## 🔍 常见问题解答

### Q1: 如何选择使用哪个 SeaweedFS 服务？

**A**: 根据数据用途选择：

- **AI-Box 服务**：用于 AI-Box 项目内的非结构化数据（治理日志、版本历史、变更提案、文件等）
- **DataLake 服务**：用于 DataLake 项目的文件备份数据

在创建存储实例时，通过 `service_type` 参数指定：

```python
storage = create_storage_from_config(config, service_type="ai_box")  # 或 "datalake"
```

### Q2: 文件存储在哪里？

**A**: 文件存储在 SeaweedFS 中，通过 S3 URI 引用。S3 URI 格式：

- `s3://bucket-name/file-path`
- 或 `http://endpoint/bucket-name/file-path`

### Q3: 如何迁移现有文件到 SeaweedFS？

**A**: 使用迁移脚本 `scripts/migration/migrate_files_to_seaweedfs.py`：

```bash
python scripts/migration/migrate_files_to_seaweedfs.py
```

### Q4: SeaweedFS 支持哪些 API？

**A**: SeaweedFS 支持两种 API：

- **S3 API**：标准 S3 兼容接口（推荐使用）
- **Filer API**：SeaweedFS 原生文件系统接口

### Q5: 如何处理文件版本管理？

**A**: 文件版本通过文件路径管理，例如：

- 原始文件：`files/{file_id}`
- 版本快照：`files/{file_id}__v{version}`

---

## 📚 相关文档

- [存储架构](./存储架构.md) - 存储架构详细说明
- [资料架构建议报告](../資料架构建议报告.md) - 架构演进建议
- [资料存储架构重构分析与计划](../資料存儲架構重構分析與計劃.md) - 重构实施计划
- [部署架构](./部署架构.md) - Kubernetes 部署说明

---

**最后更新日期**: 2025-12-29
