# start_services.sh 脚本更新说明

**创建日期**: 2025-12-29
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-29
**关联文档**: [SeaweedFS部署完成報告](./SeaweedFS部署完成報告.md)

---

## 📋 更新概述

本次更新为 `scripts/start_services.sh` 脚本添加了 SeaweedFS 双服务（AI-Box 和 DataLake）的启动和状态检查功能。

---

## ✅ 更新内容

### 1. 添加 SeaweedFS 端口配置

在服务配置部分添加了以下端口配置：

```bash
# SeaweedFS 端口配置
AI_BOX_SEAWEEDFS_MASTER_PORT=9333
AI_BOX_SEAWEEDFS_FILER_PORT=8888
AI_BOX_SEAWEEDFS_S3_PORT=8333
DATALAKE_SEAWEEDFS_MASTER_PORT=9334
DATALAKE_SEAWEEDFS_FILER_PORT=8889
DATALAKE_SEAWEEDFS_S3_PORT=8334
```

### 2. 新增启动函数

#### `start_seaweedfs_ai_box()`

- 启动 AI-Box SeaweedFS 服务
- 使用 `docker-compose.seaweedfs.yml` 配置文件
- 检查端口 8333（S3 API）确认服务状态

#### `start_seaweedfs_datalake()`

- 启动 DataLake SeaweedFS 服务
- 使用 `docker-compose.seaweedfs-datalake.yml` 配置文件
- 检查端口 8334（S3 API）确认服务状态

#### `start_seaweedfs_docker()`（更新）

- 兼容旧版本的函数
- 同时启动 AI-Box 和 DataLake 两个服务

### 3. 更新状态检查函数

`check_status()` 函数现在包含 SeaweedFS 状态检查：

- **AI-Box SeaweedFS**：检查 S3 API 端口（8333）和 Filer 端口（8888）
- **DataLake SeaweedFS**：检查 S3 API 端口（8334）和 Filer 端口（8889）

### 4. 更新使用说明

`show_usage()` 函数新增以下选项：

- `seaweedfs` - 启动 SeaweedFS (AI-Box 和 DataLake)
- `seaweedfs-ai-box` - 启动 AI-Box SeaweedFS
- `seaweedfs-datalake` - 启动 DataLake SeaweedFS

### 5. 更新主函数

`main()` 函数新增以下选项处理：

- `seaweedfs-ai-box)` - 调用 `start_seaweedfs_ai_box()`
- `seaweedfs-datalake)` - 调用 `start_seaweedfs_datalake()`

---

## 📊 使用示例

### 启动所有服务（包括 SeaweedFS）

```bash
./scripts/start_services.sh all
```

### 单独启动 SeaweedFS 服务

```bash
# 启动两个 SeaweedFS 服务
./scripts/start_services.sh seaweedfs

# 只启动 AI-Box SeaweedFS
./scripts/start_services.sh seaweedfs-ai-box

# 只启动 DataLake SeaweedFS
./scripts/start_services.sh seaweedfs-datalake
```

### 检查服务状态

```bash
./scripts/start_services.sh status
```

**输出示例**：

```
=== 服務狀態檢查 ===

Worker 狀態:
✅ RQ Worker - 運行中 (PID: 48814 48810)

Dashboard 狀態:
✅ RQ Dashboard - 運行中 (端口 9181, PID: 10688)
  訪問地址: http://localhost:9181

SeaweedFS 狀態:
✅ AI-Box SeaweedFS - 運行中 (S3 API: 8333, Filer: 8888)
✅ DataLake SeaweedFS - 運行中 (S3 API: 8334, Filer: 8889)

✅ ArangoDB - 運行中 (端口 8529, PID: 48563)
✅ ChromaDB - 運行中 (端口 8001, PID: 48563)
✅ Redis - 運行中 (端口 6379, PID: 10688)
✅ FastAPI - 運行中 (端口 8000, PID: 48703)
✅ MCP Server - 運行中 (端口 8002, PID: 9322)
✅ Frontend - 運行中 (端口 3000, PID: 48783)
```

### 创建 SeaweedFS Buckets

```bash
./scripts/start_services.sh buckets
```

---

## 🔧 技术细节

### 端口检查逻辑

脚本使用 `check_port()` 函数检查以下端口：

- **AI-Box SeaweedFS**：
  - S3 API: 8333
  - Filer API: 8888
  - Master API: 9333

- **DataLake SeaweedFS**：
  - S3 API: 8334
  - Filer API: 8889
  - Master API: 9334

### Docker Compose 命令检测

脚本自动检测可用的 Docker Compose 命令：

1. 优先使用 `docker-compose`（如果存在）
2. 否则使用 `docker compose`（Docker 新版本）

### 服务启动顺序

在 `all` 选项中，服务启动顺序为：

1. SeaweedFS 服务（AI-Box 和 DataLake）
2. SeaweedFS Buckets 创建
3. ArangoDB
4. ChromaDB
5. Redis
6. FastAPI
7. MCP Server
8. Frontend
9. RQ Worker
10. RQ Dashboard

---

## ⚠️ 注意事项

1. **配置文件要求**：
   - `docker-compose.seaweedfs.yml` - AI-Box SeaweedFS 配置
   - `docker-compose.seaweedfs-datalake.yml` - DataLake SeaweedFS 配置

2. **环境变量**：
   - 脚本会自动加载 `.env` 文件中的环境变量
   - SeaweedFS 相关配置应设置在 `.env` 文件中

3. **端口冲突**：
   - 脚本会自动检测并处理端口占用问题
   - 如果端口被占用，会尝试关闭占用端口的进程

4. **服务依赖**：
   - SeaweedFS 服务可以独立启动
   - Buckets 创建需要 SeaweedFS 服务已启动

---

## 📝 更新记录

- **2025-12-29**：添加 SeaweedFS 双服务启动和状态检查功能
  - 添加端口配置
  - 添加 `start_seaweedfs_ai_box()` 函数
  - 添加 `start_seaweedfs_datalake()` 函数
  - 更新 `check_status()` 函数
  - 更新 `show_usage()` 函数
  - 更新 `main()` 函数

---

## 🔗 相关文档

- [SeaweedFS部署完成報告](./SeaweedFS部署完成報告.md) - SeaweedFS 部署详情
- [开发环境设置指南](./开发环境设置指南.md) - 环境配置说明
- [SeaweedFS 使用指南](./核心组件/系統管理/SeaweedFS使用指南.md) - SeaweedFS 详细使用说明

---

**最后更新日期**: 2025-12-29
**维护者**: Daniel Chung
