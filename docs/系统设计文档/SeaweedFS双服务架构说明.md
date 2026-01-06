# SeaweedFS 双服务架构说明

**创建日期**: 2025-12-31
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-31

---

## 📋 概述

AI-Box 系统使用 **SeaweedFS 双服务部署架构**，分别为 AI-Box 和 DataLake 项目提供独立的存储服务。

---

## 🏗️ 为什么需要两个独立的 SeaweedFS 服务？

### 架构设计原因

1. **职责分离**
   - AI-Box SeaweedFS：专门服务于 AI-Box 项目的存储需求
   - DataLake SeaweedFS：专门服务于 DataLake 项目的存储需求
   - 两个项目的数据完全隔离，避免相互影响

2. **独立扩展**
   - 两个服务可以根据各自项目的需求独立扩展
   - AI-Box 可能需要更多存储空间用于治理日志和历史版本
   - DataLake 可能需要更多存储空间用于文件备份

3. **数据隔离**
   - 避免两个项目之间的数据混杂
   - 每个项目的数据存储在独立的服务中，提高安全性

4. **灵活部署**
   - 可以根据实际需求选择不同的部署策略
   - 可以单独停止或启动某个服务，不影响另一个

---

## 🔧 三个启动选项说明

### 1. `seaweedfs` - 启动两个服务（推荐用于完整环境）

**功能**：同时启动 AI-Box 和 DataLake 两个 SeaweedFS 服务

**使用场景**：
- 开发环境完整启动
- 需要同时使用两个项目的存储功能
- 使用 `all` 选项启动所有服务时

**实现**：调用 `start_seaweedfs_ai_box()` 和 `start_seaweedfs_datalake()`

**示例**：
```bash
./scripts/start_services.sh seaweedfs
```

### 2. `seaweedfs-ai-box` - 只启动 AI-Box 服务

**功能**：只启动 AI-Box SeaweedFS 服务

**使用场景**：
- 只需要使用 AI-Box 项目的存储功能
- DataLake 项目暂不需要存储服务
- 节省资源（只启动需要的服务）

**存储内容**：
- 治理相关日志（审计日志、系统日志）
- 版本历史记录（配置和 Ontology 的历史版本）
- 变更提案记录
- DataLake 元数据（dictionary 和 schema 定义）
- AI-Box 项目其他非结构化数据

**端口配置**：
- Master: 9333
- Filer API: 8888
- S3 API: 8333

**示例**：
```bash
./scripts/start_services.sh seaweedfs-ai-box
```

### 3. `seaweedfs-datalake` - 只启动 DataLake 服务

**功能**：只启动 DataLake SeaweedFS 服务

**使用场景**：
- 只需要使用 DataLake 项目的存储功能
- AI-Box 项目暂不需要存储服务
- 节省资源（只启动需要的服务）

**存储内容**：
- 文件备份数据
- DataLake 项目相关的存储需求

**端口配置**：
- Master: 9334（避免与 AI-Box 冲突）
- Filer API: 8889
- S3 API: 8334

**示例**：
```bash
./scripts/start_services.sh seaweedfs-datalake
```

---

## 📊 服务架构对比

| 特性 | AI-Box SeaweedFS | DataLake SeaweedFS |
|------|-----------------|-------------------|
| **服务名称** | `seaweedfs-ai-box` | `seaweedfs-datalake` |
| **主要用途** | AI-Box 项目存储 | DataLake 项目存储 |
| **Master 端口** | 9333 | 9334 |
| **Filer API 端口** | 8888 | 8889 |
| **S3 API 端口** | 8333 | 8334 |
| **主要存储内容** | 治理日志、版本历史、变更提案、DataLake 元数据 | 文件备份数据 |
| **Buckets 数量** | 6 个 | 2 个 |

---

## 🚀 使用建议

### 开发环境

**推荐**：使用 `seaweedfs` 选项同时启动两个服务
```bash
./scripts/start_services.sh all  # 包含 seaweedfs
# 或单独启动
./scripts/start_services.sh seaweedfs
```

### 生产环境

**推荐**：根据实际需求选择启动选项
- 如果只需要 AI-Box 功能：`seaweedfs-ai-box`
- 如果只需要 DataLake 功能：`seaweedfs-datalake`
- 如果需要两个项目都使用：`seaweedfs`

### 资源受限环境

如果资源有限，可以只启动需要的服务：
```bash
# 只启动 AI-Box 服务
./scripts/start_services.sh seaweedfs-ai-box

# 只启动 DataLake 服务
./scripts/start_services.sh seaweedfs-datalake
```

---

## 📝 相关文档

- [存储架构文档](./核心组件/存储架构.md) - 详细的存储架构说明
- [SeaweedFS 使用指南](./核心组件/系統管理/SeaweedFS使用指南.md) - SeaweedFS 使用说明
- [start_services 脚本更新说明](./start_services脚本更新说明.md) - 脚本功能说明

---

**最后更新日期**: 2025-12-31
**维护人**: Daniel Chung

