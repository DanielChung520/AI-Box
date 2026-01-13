# SeaweedFS 使用指南

**创建日期**: 2025-12-29
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-13
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
AI_BOX_SEAWEEDFS_S3_ENDPOINT=http://localhost:8333
AI_BOX_SEAWEEDFS_S3_ACCESS_KEY=admin
AI_BOX_SEAWEEDFS_S3_SECRET_KEY=admin123
AI_BOX_SEAWEEDFS_USE_SSL=false
AI_BOX_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8888

# DataLake 专案的 SeaweedFS 配置
DATALAKE_SEAWEEDFS_S3_ENDPOINT=http://localhost:8334
DATALAKE_SEAWEEDFS_S3_ACCESS_KEY=admin
DATALAKE_SEAWEEDFS_S3_SECRET_KEY=admin123
DATALAKE_SEAWEEDFS_USE_SSL=false
DATALAKE_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8889
DATALAKE_SEAWEEDFS_MASTER_HOST=localhost
DATALAKE_SEAWEEDFS_MASTER_PORT=9334
```

### 端口配置说明

**AI-Box SeaweedFS 服务**：

| 服务 | 容器内端口 | 主机端口 | 说明 |
|------|-----------|---------|------|
| Master API | 9333 | 9333 | 元数据管理 |
| Filer API | 8888 | 8888 | 文件系统接口 |
| S3 API | 8333 | 8333 | S3 兼容接口 |

**DataLake SeaweedFS 服务**：

| 服务 | 容器内端口 | 主机端口 | 说明 |
|------|-----------|---------|------|
| Master API | 9333 | 9334 | 元数据管理 |
| Filer API | 8888 | 8889 | 文件系统接口 |
| S3 API | 8333 | 8334 | S3 兼容接口 |

### S3 API 启用配置

⚠️ **重要**：SeaweedFS Filer 默认不启用 S3 API，必须在 Docker Compose 配置中显式启用。

**AI-Box 服务配置**（`docker-compose.seaweedfs.yml`）：

```yaml
seaweedfs-filer:
  command: "filer -master=seaweedfs-master:9333 -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json"
  volumes:
    - seaweedfs-ai-box-s3-config:/etc/seaweedfs
```

**DataLake 服务配置**（`docker-compose.seaweedfs-datalake.yml`）：

```yaml
seaweedfs-datalake-filer:
  command: "filer -master=seaweedfs-datalake-master:9333 -s3 -s3.port=8333 -s3.config=/etc/seaweedfs/s3.json"
  volumes:
    - seaweedfs-datalake-s3-config:/etc/seaweedfs
```

**S3 配置文件**（`s3.json`）：

创建 Docker volume 并添加 S3 配置文件：

```bash
# AI-Box 服务
docker volume create seaweedfs-ai-box-s3-config

# DataLake 服务
docker volume create seaweedfs-datalake-s3-config
```

配置文件内容（`s3.json`）：

```json
{
  "identities": [
    {
      "name": "admin",
      "credentials": [
        {
          "accessKey": "admin",
          "secretKey": "admin123"
        }
      ],
      "actions": [
        "Admin",
        "Read",
        "Write"
      ]
    }
  ]
}
```

**配置步骤**：

1. 创建临时目录并生成配置文件：

   ```bash
   mkdir -p /tmp/seaweedfs-s3-config
   cat > /tmp/seaweedfs-s3-config/s3.json << 'EOF'
   {
     "identities": [
       {
         "name": "admin",
         "credentials": [
           {
             "accessKey": "admin",
             "secretKey": "admin123"
           }
         ],
         "actions": [
           "Admin",
           "Read",
           "Write"
         ]
       }
     ]
   }
   EOF
   ```

2. 复制配置文件到 Docker volume：

   ```bash
   # AI-Box 服务
   docker run --rm \
     -v /tmp/seaweedfs-s3-config:/source \
     -v seaweedfs-ai-box-s3-config:/target \
     alpine sh -c 'cp -r /source/* /target/'

   # DataLake 服务
   docker run --rm \
     -v /tmp/seaweedfs-s3-config:/source \
     -v seaweedfs-datalake-s3-config:/target \
     alpine sh -c 'cp -r /source/* /target/'
   ```

3. 重启容器：

   ```bash
   docker-compose -f docker-compose.seaweedfs.yml up -d
   docker-compose -f docker-compose.seaweedfs-datalake.yml up -d
   ```

4. 验证 S3 API 已启用：

   ```bash
   # 检查日志
   docker logs seaweedfs-ai-box-filer | grep -i s3
   docker logs seaweedfs-datalake-filer | grep -i s3

   # 测试连接
   curl -v http://localhost:8333/
   curl -v http://localhost:8334/
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

## 🌐 Web Dashboard

SeaweedFS 提供了多个 Web Dashboard 用于监控和管理：

### Master Server Dashboard

**访问地址**：

- **AI-Box 服务**：`http://localhost:9333/`
- **DataLake 服务**：`http://localhost:9334/`

**功能**：

- 查看集群状态
- 监控 Volume 节点
- 查看系统信息
- 管理拓扑结构

### Filer Server Dashboard

**访问地址**：

- **AI-Box 服务**：`http://localhost:8888/`
- **DataLake 服务**：`http://localhost:8889/`

**功能**：

- 浏览文件系统
- 上传/下载文件
- 创建/删除目录
- 查看文件元数据

### Volume Server Dashboard

**访问地址**（需要端口映射）：

- **AI-Box Volume**：`http://localhost:8080/ui/index.html`
- **DataLake Volume**：`http://localhost:8081/ui/index.html`

**功能**：

- 查看 Volume 状态
- 监控存储使用情况
- 查看 Volume 节点信息

**使用说明**：

1. 在浏览器中打开对应的 URL
2. Dashboard 会自动显示当前服务的状态信息
3. 可以通过 Dashboard 进行基本的文件操作和管理

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

⚠️ **重要提示**：S3 API 需要显式启用。如果 Filer 启动命令中没有 `-s3` 参数，S3 API 将无法使用，即使端口已映射也会返回 "Empty reply from server" 错误。

### Q6: 为什么 S3 API 连接失败，返回 "Empty reply from server"？

**A**: 这通常是因为 S3 API 未启用。检查步骤：

1. **检查 Filer 启动命令**：

   ```bash
   docker inspect seaweedfs-ai-box-filer --format='{{.Config.Cmd}}'
   docker inspect seaweedfs-datalake-filer --format='{{.Config.Cmd}}'
   ```

   应该包含 `-s3` 参数。

2. **检查容器日志**：

   ```bash
   docker logs seaweedfs-ai-box-filer | grep -i s3
   docker logs seaweedfs-datalake-filer | grep -i s3
   ```

   应该看到 S3 API 启动的相关日志。

3. **检查 S3 配置文件**：

   ```bash
   docker exec seaweedfs-ai-box-filer cat /etc/seaweedfs/s3.json
   docker exec seaweedfs-datalake-filer cat /etc/seaweedfs/s3.json
   ```

   配置文件应该存在且格式正确。

4. **修复方法**：
   - 更新 Docker Compose 配置，添加 `-s3` 参数和 S3 配置文件
   - 创建 S3 配置 volume 并添加配置文件
   - 重启容器

详细修复步骤请参考本文档的 "S3 API 启用配置" 章节。

### Q5: 如何处理文件版本管理？

**A**: 文件版本通过文件路径管理，例如：

- 原始文件：`files/{file_id}`
- 版本快照：`files/{file_id}__v{version}`

### Q7: SeaweedFS 是否有 HTTP Dashboard？

**A**: 是的，SeaweedFS 提供了多个 Web Dashboard：

#### Master Server Dashboard

- **AI-Box 服务**：`http://localhost:9333/`
- **DataLake 服务**：`http://localhost:9334/`

功能包括：

- 集群状态查看
- Volume 节点管理
- 系统信息显示

#### Filer Server Dashboard

- **AI-Box 服务**：`http://localhost:8888/`
- **DataLake 服务**：`http://localhost:8889/`

功能包括：

- 文件系统浏览
- 文件上传/下载
- 目录管理

#### Volume Server Dashboard

- **AI-Box Volume**：`http://localhost:8080/ui/index.html`（如果端口已映射）
- **DataLake Volume**：`http://localhost:8081/ui/index.html`（如果端口已映射）

**访问方式**：

直接在浏览器中打开上述 URL 即可访问对应的 Dashboard。

**注意事项**：

- 如果使用 Docker 部署，确保端口已正确映射
- Volume Server 的 Dashboard 端口需要显式映射才能从主机访问

---

## 📚 相关文档

- [存储架构](./存储架构.md) - 存储架构详细说明
- [资料架构建议报告](../資料架构建议报告.md) - 架构演进建议
- [资料存储架构重构分析与计划](../資料存儲架構重構分析與計劃.md) - 重构实施计划
- [部署架构](./部署架构.md) - Kubernetes 部署说明

---

**最后更新日期**: 2026-01-13
