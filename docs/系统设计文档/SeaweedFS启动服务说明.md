# SeaweedFS 启动服务说明

**创建日期**: 2025-12-29
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-29
**关联文档**: [开发环境设置指南](./开发环境设置指南.md)、[SeaweedFS 使用指南](./核心组件/SeaweedFS使用指南.md)

---

## 📋 概述

本文档说明在启动服务脚本（`scripts/start_services.sh`）中需要添加的内容，以支持 SeaweedFS 服务的启动和初始化。

---

## 🔧 需要添加的内容

### 1. SeaweedFS Docker Compose 启动（可选）

如果使用 Docker Compose 在本地运行 SeaweedFS，需要在启动脚本中添加以下内容：

```bash
# 启动 SeaweedFS（Docker Compose）
start_seaweedfs_docker() {
    local compose_file="docker-compose.seaweedfs.yml"

    if [ ! -f "$compose_file" ]; then
        echo "未找到 $compose_file，跳過 SeaweedFS Docker 啟動"
        return 1
    fi

    echo "檢查 SeaweedFS 是否已運行..."

    # 檢查 S3 API 端口（8333）
    if nc -z localhost 8333 2>/dev/null || curl -s http://localhost:8333 > /dev/null 2>&1; then
        echo "SeaweedFS 已在運行（端口 8333）"
        return 0
    fi

    echo "啟動 SeaweedFS（Docker Compose）..."

    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$compose_file" up -d
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$compose_file" up -d
    else
        echo "錯誤：未找到 docker-compose 或 docker compose 命令"
        return 1
    fi

    # 等待 SeaweedFS 啟動
    echo "等待 SeaweedFS 啟動..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost 8333 2>/dev/null || curl -s http://localhost:8333 > /dev/null 2>&1; then
            echo "SeaweedFS 啟動成功"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "錯誤：SeaweedFS 啟動超時"
    return 1
}
```

### 2. 创建 SeaweedFS Buckets

在 SeaweedFS 启动后，需要创建必要的 Buckets：

```bash
# 創建 SeaweedFS Buckets
create_seaweedfs_buckets() {
    local script_path="scripts/migration/create_seaweedfs_buckets.py"

    if [ ! -f "$script_path" ]; then
        echo "警告：未找到 $script_path，跳過 Buckets 創建"
        return 1
    fi

    # 檢查是否配置了 SeaweedFS 環境變數
    if [ -z "$AI_BOX_SEAWEEDFS_S3_ENDPOINT" ] && [ -z "$DATALAKE_SEAWEEDFS_S3_ENDPOINT" ]; then
        echo "警告：未配置 SeaweedFS 環境變數，跳過 Buckets 創建"
        echo "提示：如需使用 SeaweedFS，請在 .env 文件中配置相關環境變數"
        return 1
    fi

    echo "創建 SeaweedFS Buckets..."

    # 檢查 Python 環境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # 運行 Buckets 創建腳本
    if python "$script_path" --service all; then
        echo "SeaweedFS Buckets 創建成功"
        return 0
    else
        echo "警告：SeaweedFS Buckets 創建失敗或已存在"
        return 1
    fi
}
```

### 3. 主函数调用顺序

在主函数中，按以下顺序调用：

```bash
main() {
    echo "開始啟動 AI-Box 系統服務..."

    # 加載環境變數
    if [ -f ".env" ]; then
        echo "加載環境變數..."
        set -a
        source .env
        set +a
    fi

    # 1. 啟動 SeaweedFS（如果使用 Docker Compose）
    if [ "$USE_SEAWEEDFS_DOCKER" = "true" ] || [ -f "docker-compose.seaweedfs.yml" ]; then
        start_seaweedfs_docker

        # 創建 Buckets
        create_seaweedfs_buckets
    else
        echo "跳過 SeaweedFS Docker 啟動（未配置或使用 Kubernetes）"
        echo "提示：如果使用 Kubernetes，請確保 SeaweedFS 服務已部署"

        # 即使不使用 Docker，也嘗試創建 Buckets（可能連接到遠程 SeaweedFS）
        create_seaweedfs_buckets
    fi

    # 2. 檢查其他服務（ArangoDB、Redis、ChromaDB 等）
    # ... 其他服務檢查 ...

    echo "服務啟動完成！"
}
```

---

## 📝 完整的启动脚本示例

以下是完整的启动脚本示例（`scripts/start_services.sh`）：

```bash
#!/bin/bash

# 代碼功能說明：啟動 AI-Box 系統所需的所有服務，包括 SeaweedFS、ArangoDB、Redis、ChromaDB 等
# 創建日期：2025-12-29
# 創建人：Daniel Chung
# 最後修改日期：2025-12-29

set -e  # 遇到錯誤時退出

# 獲取腳本所在目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 切換到項目根目錄
cd "$PROJECT_ROOT"

# 啟動 SeaweedFS（Docker Compose）
start_seaweedfs_docker() {
    local compose_file="docker-compose.seaweedfs.yml"

    if [ ! -f "$compose_file" ]; then
        echo "未找到 $compose_file，跳過 SeaweedFS Docker 啟動"
        return 1
    fi

    echo "檢查 SeaweedFS 是否已運行..."

    # 檢查 S3 API 端口（8333）
    if nc -z localhost 8333 2>/dev/null || curl -s http://localhost:8333 > /dev/null 2>&1; then
        echo "SeaweedFS 已在運行（端口 8333）"
        return 0
    fi

    echo "啟動 SeaweedFS（Docker Compose）..."

    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$compose_file" up -d
    elif command -v docker &> /dev/null && docker compose version &> /dev/null; then
        docker compose -f "$compose_file" up -d
    else
        echo "錯誤：未找到 docker-compose 或 docker compose 命令"
        return 1
    fi

    # 等待 SeaweedFS 啟動
    echo "等待 SeaweedFS 啟動..."
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if nc -z localhost 8333 2>/dev/null || curl -s http://localhost:8333 > /dev/null 2>&1; then
            echo "SeaweedFS 啟動成功"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    echo "錯誤：SeaweedFS 啟動超時"
    return 1
}

# 創建 SeaweedFS Buckets
create_seaweedfs_buckets() {
    local script_path="scripts/migration/create_seaweedfs_buckets.py"

    if [ ! -f "$script_path" ]; then
        echo "警告：未找到 $script_path，跳過 Buckets 創建"
        return 1
    fi

    # 檢查是否配置了 SeaweedFS 環境變數
    if [ -z "$AI_BOX_SEAWEEDFS_S3_ENDPOINT" ] && [ -z "$DATALAKE_SEAWEEDFS_S3_ENDPOINT" ]; then
        echo "警告：未配置 SeaweedFS 環境變數，跳過 Buckets 創建"
        echo "提示：如需使用 SeaweedFS，請在 .env 文件中配置相關環境變數"
        return 1
    fi

    echo "創建 SeaweedFS Buckets..."

    # 檢查 Python 環境
    if [ -d "venv" ]; then
        source venv/bin/activate
    fi

    # 運行 Buckets 創建腳本
    if python "$script_path" --service all; then
        echo "SeaweedFS Buckets 創建成功"
        return 0
    else
        echo "警告：SeaweedFS Buckets 創建失敗或已存在"
        return 1
    fi
}

# 主函數
main() {
    echo "開始啟動 AI-Box 系統服務..."

    # 加載環境變數
    if [ -f ".env" ]; then
        echo "加載環境變數..."
        set -a
        source .env
        set +a
    fi

    # 1. 啟動 SeaweedFS（如果使用 Docker Compose）
    if [ "$USE_SEAWEEDFS_DOCKER" = "true" ] || [ -f "docker-compose.seaweedfs.yml" ]; then
        start_seaweedfs_docker
        echo ""

        # 創建 Buckets
        create_seaweedfs_buckets
        echo ""
    else
        echo "跳過 SeaweedFS Docker 啟動（未配置或使用 Kubernetes）"
        echo "提示：如果使用 Kubernetes，請確保 SeaweedFS 服務已部署"
        echo ""

        # 即使不使用 Docker，也嘗試創建 Buckets（可能連接到遠程 SeaweedFS）
        create_seaweedfs_buckets
        echo ""
    fi

    # 2. 檢查其他服務（ArangoDB、Redis、ChromaDB 等）
    # ... 其他服務檢查 ...

    echo "服務啟動完成！"
    echo ""
    echo "下一步："
    echo "  1. 確保所有服務都已啟動"
    echo "  2. 運行 'python scripts/migration/create_schema.py' 初始化 ArangoDB Schema"
    echo "  3. 運行 'python -m api.main' 啟動 API 服務"
    echo "  4. 運行 'python -m workers.worker' 啟動 Worker 服務（另一個終端）"
}

# 執行主函數
main "$@"
```

---

## 🐳 Docker Compose 配置文件

如果需要使用 Docker Compose 启动 SeaweedFS，需要创建 `docker-compose.seaweedfs.yml` 文件：

```yaml
version: '3.8'

services:
  seaweedfs-master:
    image: chrislusf/seaweedfs:latest
    command: "master -ip=seaweedfs-master -port=9333"
    ports:
      - "9333:9333"
    networks:
      - seaweedfs-network

  seaweedfs-volume:
    image: chrislusf/seaweedfs:latest
    command: "volume -mserver=seaweedfs-master:9333 -port=8080"
    depends_on:
      - seaweedfs-master
    networks:
      - seaweedfs-network

  seaweedfs-filer:
    image: chrislusf/seaweedfs:latest
    command: "filer -master=seaweedfs-master:9333"
    ports:
      - "8888:8888"  # Filer API
      - "8333:8333"  # S3 API
    depends_on:
      - seaweedfs-master
      - seaweedfs-volume
    networks:
      - seaweedfs-network

networks:
  seaweedfs-network:
    driver: bridge
```

---

## 📋 启动顺序说明

### 本地开发环境（使用 Docker Compose）

1. **启动 SeaweedFS**：使用 Docker Compose 启动 SeaweedFS 服务
2. **创建 Buckets**：运行 `create_seaweedfs_buckets.py` 脚本创建必要的 Buckets
3. **启动其他服务**：ArangoDB、Redis、ChromaDB 等
4. **初始化数据库**：运行 `create_schema.py` 初始化 ArangoDB Schema
5. **启动应用服务**：运行 API 服务和 Worker 服务

### Kubernetes 环境

1. **确保 SeaweedFS 已部署**：使用 Kubernetes 部署配置文件部署 SeaweedFS
2. **创建 Buckets**：运行 `create_seaweedfs_buckets.py` 脚本创建必要的 Buckets（连接到 Kubernetes 中的 SeaweedFS 服务）
3. **启动其他服务**：ArangoDB、Redis、ChromaDB 等
4. **初始化数据库**：运行 `create_schema.py` 初始化 ArangoDB Schema
5. **启动应用服务**：运行 API 服务和 Worker 服务

---

## ⚙️ 环境变量配置

确保在 `.env` 文件中配置了 SeaweedFS 相关环境变量：

```bash
# AI-Box 项目的 SeaweedFS 配置
AI_BOX_SEAWEEDFS_S3_ENDPOINT=http://localhost:8333  # 本地开发
# 或
AI_BOX_SEAWEEDFS_S3_ENDPOINT=http://seaweedfs-ai-box-filer:8333  # Kubernetes

AI_BOX_SEAWEEDFS_S3_ACCESS_KEY=your-access-key
AI_BOX_SEAWEEDFS_S3_SECRET_KEY=your-secret-key
AI_BOX_SEAWEEDFS_USE_SSL=false
AI_BOX_SEAWEEDFS_FILER_ENDPOINT=http://localhost:8888  # 本地开发
# 或
AI_BOX_SEAWEEDFS_FILER_ENDPOINT=http://seaweedfs-ai-box-filer:8888  # Kubernetes
```

---

## 🔍 验证

启动服务后，可以使用以下命令验证 SeaweedFS 是否正常运行：

```bash
# 检查 SeaweedFS S3 API
curl http://localhost:8333

# 检查 SeaweedFS Filer API
curl http://localhost:8888

# 测试创建 Buckets
python scripts/migration/create_seaweedfs_buckets.py --service all --dry-run
```

---

## 📚 相关文档

- [开发环境设置指南](./开发环境设置指南.md) - 完整的开发环境配置说明
- [SeaweedFS 使用指南](./核心组件/SeaweedFS使用指南.md) - SeaweedFS 详细使用说明
- [存储架构](./核心组件/存储架构.md) - 存储架构详细说明

---

**最后更新日期**: 2025-12-29
