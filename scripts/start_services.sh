#!/bin/bash
# 代碼功能說明: 啟動 AI-Box 服務腳本

# 加載 .env 文件（如果存在）
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服務端口配置
ARANGODB_PORT=8529
QDRANT_REST_PORT=6333
QDRANT_GRPC_PORT=6334
FASTAPI_PORT=8000
REDIS_PORT=6379
MCP_SERVER_PORT=8002
FRONTEND_PORT=3000
OLLAMA_PORT=11434

# SeaweedFS 端口配置
AI_BOX_SEAWEEDFS_MASTER_PORT=9333
AI_BOX_SEAWEEDFS_FILER_PORT=8888
AI_BOX_SEAWEEDFS_S3_PORT=8333
DATALAKE_SEAWEEDFS_MASTER_PORT=9334
DATALAKE_SEAWEEDFS_FILER_PORT=8889
DATALAKE_SEAWEEDFS_S3_PORT=8334

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日誌目錄
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 函數：檢查端口是否被占用（含 Docker 綁定端口，Linux 下 lsof 可能偵測不到）
check_port() {
    local port=$1
    # 检查 LISTEN 状态的端口（本機進程）
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用（LISTEN 状态）
    fi
    # 检查其他状态的端口（包括 CLOSED）
    if lsof -ti :$port >/dev/null 2>&1; then
        return 0  # 端口被占用（其他状态）
    fi
    # Linux 下 Docker 綁定的端口 lsof 可能偵測不到，改用 ss 或 /dev/tcp
    if command -v ss &>/dev/null && ss -tln 2>/dev/null | grep -qE ":${port}([^0-9]|\$)"; then
        return 0
    fi
    if (echo >/dev/tcp/127.0.0.1/$port) 2>/dev/null; then
        return 0
    fi
    return 1  # 端口未被占用
}

# 函數：關閉占用端口的進程
# 函數：關閉占用端口的進程（但跳過 Docker 容器）
kill_port() {
    local port=$1
    local service_name=$2

    if check_port $port; then
        # 檢查是否是 Docker 容器占用端口
        if docker ps --format '{{.Ports}}' 2>/dev/null | grep -q ":$port->"; then
            echo -e "${GREEN}端口 $port 被 Docker 容器占用，跳過關閉${NC}"
            return 0
        fi

        echo -e "${YELLOW}檢測到端口 $port 已被占用，正在關閉...${NC}"
        local pids=$(lsof -ti :$port)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                local proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                # 跳過 Docker 相關進程
                if [[ "$proc_name" == *"docker"* ]] || [[ "$proc_name" == *"com.docker"* ]]; then
                    echo -e "${GREEN}  跳過 Docker 進程 $pid ($proc_name) - 端口 $port${NC}"
                    continue
                fi
                echo -e "${YELLOW}  關閉進程 $pid ($proc_name) - 端口 $port${NC}"
                # 先嘗試優雅關閉
                kill $pid 2>/dev/null || true
                sleep 1
                # 如果還在運行，強制關閉
                if kill -0 $pid 2>/dev/null; then
                    kill -9 $pid 2>/dev/null || true
                fi
            done
            # 等待進程完全退出
            sleep 2
            # 再次檢查
            local remaining_pids=$(lsof -ti :$port 2>/dev/null)
            if [ -n "$remaining_pids" ]; then
                # 再次過濾 Docker 進程
                local non_docker_pids=""
                for pid in $remaining_pids; do
                    local proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
                    if [[ "$proc_name" != *"docker"* ]] && [[ "$proc_name" != *"com.docker"* ]]; then
                        non_docker_pids="$non_docker_pids $pid"
                    fi
                done
                if [ -n "$non_docker_pids" ]; then
                    echo -e "${RED}  警告: 端口 $port 仍被占用 (PID: $non_docker_pids)${NC}"
                    echo -e "${YELLOW}  嘗試強制關閉...${NC}"
                    for pid in $non_docker_pids; do
                        kill -9 $pid 2>/dev/null || true
                    done
                    sleep 1
                    if check_port $port; then
                        # 再次檢查是否是 Docker
                        if ! docker ps --format '{{.Ports}}' 2>/dev/null | grep -q ":$port->"; then
                            echo -e "${RED}  錯誤: 無法釋放端口 $port${NC}"
                            return 1
                        fi
                    fi
                fi
            fi
            echo -e "${GREEN}  端口 $port 已釋放${NC}"
        fi
    fi
    return 0
}
# 函數：根據進程名稱殺死進程
kill_process_by_name() {
    local name=$1
    local pids=$(ps aux | grep "$name" | grep -v grep | awk '{print $2}')

    if [ -n "$pids" ]; then
        echo -e "${YELLOW}發現 $name 進程，正在關閉...${NC}"
        for pid in $pids; do
            echo -e "${YELLOW}  關閉進程 $pid ($name)${NC}"
            kill $pid 2>/dev/null || true
            sleep 1
            if kill -0 $pid 2>/dev/null; then
                kill -9 $pid 2>/dev/null || true
            fi
        done
        echo -e "${GREEN}  $name 進程已清理${NC}"
    fi
}

# 函數：啟動 ArangoDB
start_arangodb() {
    echo -e "${BLUE}=== 啟動 ArangoDB ===${NC}"

    kill_port $ARANGODB_PORT "ArangoDB"

    # 檢查 Docker 是否安裝
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}錯誤: Docker 未安裝${NC}"
        echo -e "${YELLOW}請先安裝 Docker Desktop: https://www.docker.com/products/docker-desktop${NC}"
        return 1
    fi

    # 檢查 Docker daemon 是否運行
    if ! docker ps &> /dev/null 2>&1; then
        echo -e "${RED}錯誤: Docker daemon 未運行${NC}"
        echo -e "${YELLOW}請執行以下操作之一：${NC}"
        echo -e "${YELLOW}  1. 啟動 Docker Desktop 應用程式${NC}"
        echo -e "${YELLOW}  2. 或運行: open -a Docker${NC}"
        echo ""

        # 嘗試自動啟動 Docker Desktop (macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${BLUE}嘗試自動啟動 Docker Desktop...${NC}"
            if open -a Docker 2>/dev/null; then
                echo -e "${GREEN}已嘗試啟動 Docker Desktop，請等待其完全啟動後重新運行此命令${NC}"
                echo -e "${YELLOW}提示: Docker Desktop 通常需要 10-30 秒才能完全啟動${NC}"
            else
                echo -e "${YELLOW}無法自動啟動 Docker Desktop，請手動啟動${NC}"
            fi
        fi

        return 1
    fi

    # 查找 ArangoDB 容器
    local container=$(docker ps -a --format '{{.Names}}' | grep -i arango | head -1)
    if [ -n "$container" ]; then
        echo -e "${GREEN}發現 ArangoDB Docker 容器: $container${NC}"

        # 檢查容器是否已在運行
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            echo -e "${GREEN}✅ ArangoDB 已在運行 (端口 $ARANGODB_PORT)${NC}"
            echo -e "${GREEN}   Web UI: http://localhost:$ARANGODB_PORT${NC}"
            return 0
        fi

        # 啟動容器
        echo -e "${GREEN}啟動 ArangoDB 容器...${NC}"
        docker start "$container"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 啟動 ArangoDB 容器失敗${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi

        sleep 5

        if check_port $ARANGODB_PORT; then
            echo -e "${GREEN}✅ ArangoDB 已啟動 (端口 $ARANGODB_PORT)${NC}"
            echo -e "${GREEN}   Web UI: http://localhost:$ARANGODB_PORT${NC}"
            return 0
        else
            echo -e "${RED}❌ ArangoDB 啟動失敗（端口未監聽）${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}未找到 ArangoDB Docker 容器${NC}"
        echo -e "${BLUE}正在創建 ArangoDB 容器...${NC}"

        # 從環境變數獲取密碼，如果沒有則使用默認值
        ARANGO_PASSWORD=${ARANGO_ROOT_PASSWORD:-"changeme"}

        if docker run -d \
            -p $ARANGODB_PORT:8529 \
            -e ARANGO_ROOT_PASSWORD="$ARANGO_PASSWORD" \
            --name arangodb \
            arangodb/arangodb:latest; then
            echo -e "${GREEN}✅ ArangoDB 容器已創建${NC}"
            echo -e "${YELLOW}   密碼: $ARANGO_PASSWORD${NC}"
            echo -e "${YELLOW}   提示: 建議設置環境變數 ARANGO_ROOT_PASSWORD 來使用自定義密碼${NC}"
            sleep 5

            if check_port $ARANGODB_PORT; then
                echo -e "${GREEN}✅ ArangoDB 已啟動 (端口 $ARANGODB_PORT)${NC}"
                echo -e "${GREEN}   Web UI: http://localhost:$ARANGODB_PORT${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ 容器已創建，但端口尚未就緒，請稍後檢查${NC}"
                return 0
            fi
        else
            echo -e "${RED}❌ 創建 ArangoDB 容器失敗${NC}"
            return 1
        fi
    fi
}


# 函數：啟動 Qdrant（向量數據庫，取代 ChromaDB）
start_qdrant() {
    echo -e "${BLUE}=== 啟動 Qdrant 向量數據庫 ===${NC}"

    kill_port $QDRANT_REST_PORT "Qdrant REST"
    kill_port $QDRANT_GRPC_PORT "Qdrant gRPC"

    # 檢查 Docker 是否安裝
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}錯誤: Docker 未安裝${NC}"
        echo -e "${YELLOW}請先安裝 Docker Desktop: https://www.docker.com/products/docker-desktop${NC}"
        return 1
    fi

    # 檢查 Docker daemon 是否運行
    if ! docker ps &> /dev/null 2>&1; then
        echo -e "${RED}錯誤: Docker daemon 未運行${NC}"
        echo -e "${YELLOW}請執行以下操作之一：${NC}"
        echo -e "${YELLOW}  1. 啟動 Docker Desktop 應用程式${NC}"
        echo -e "${YELLOW}  2. 或運行: open -a Docker${NC}"
        echo ""

        # 嘗試自動啟動 Docker Desktop (macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${BLUE}嘗試自動啟動 Docker Desktop...${NC}"
            if open -a Docker 2>/dev/null; then
                echo -e "${GREEN}已嘗試啟動 Docker Desktop，請等待其完全啟動後重新運行此命令${NC}"
                echo -e "${YELLOW}提示: Docker Desktop 通常需要 10-30 秒才能完全啟動${NC}"
            else
                echo -e "${YELLOW}無法自動啟動 Docker Desktop，請手動啟動${NC}"
            fi
        fi

        return 1
    fi

    # 查找 Qdrant 容器
    local container=$(docker ps -a --format '{{.Names}}' | grep -i qdrant | head -1)
    if [ -n "$container" ]; then
        echo -e "${GREEN}發現 Qdrant Docker 容器: $container${NC}"

        # 檢查容器是否已在運行
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            echo -e "${GREEN}✅ Qdrant 已在運行 (端口 $QDRANT_REST_PORT / $QDRANT_GRPC_PORT)${NC}"
            echo -e "${GREEN}   REST API: http://localhost:$QDRANT_REST_PORT${NC}"
            echo -e "${GREEN}   gRPC API: localhost:$QDRANT_GRPC_PORT${NC}"
            echo -e "${GREEN}   Dashboard: http://localhost:$QDRANT_REST_PORT/dashboard${NC}"
            return 0
        fi

        # 啟動容器
        echo -e "${GREEN}啟動 Qdrant 容器...${NC}"
        docker start "$container"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 啟動 Qdrant 容器失敗${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi

        sleep 5

        if check_port $QDRANT_REST_PORT; then
            echo -e "${GREEN}✅ Qdrant 已啟動 (端口 $QDRANT_REST_PORT)${NC}"
            echo -e "${GREEN}   Dashboard: http://localhost:$QDRANT_REST_PORT/dashboard${NC}"
            return 0
        else
            echo -e "${RED}❌ Qdrant 啟動失敗（端口未監聽）${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}未找到 Qdrant Docker 容器${NC}"
        echo -e "${BLUE}正在創建 Qdrant 容器...${NC}"

        # 從環境變數獲取配置
        QDRANT_DATA_DIR=${QDRANT_DATA_DIR:-"./data/qdrant"}

        # 創建持久化目錄（如果不存在）
        mkdir -p "$QDRANT_DATA_DIR"

        if docker run -d \
            -p $QDRANT_REST_PORT:6333 \
            -p $QDRANT_GRPC_PORT:6334 \
            -v "$(pwd)/$QDRANT_DATA_DIR:/qdrant/storage" \
            --name qdrant \
            qdrant/qdrant:latest; then
            echo -e "${GREEN}✅ Qdrant 容器已創建${NC}"
            echo -e "${GREEN}   持久化目錄: $QDRANT_DATA_DIR${NC}"
            sleep 5

            if check_port $QDRANT_REST_PORT; then
                echo -e "${GREEN}✅ Qdrant 已啟動 (端口 $QDRANT_REST_PORT)${NC}"
                echo -e "${GREEN}   Dashboard: http://localhost:$QDRANT_REST_PORT/dashboard${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ 容器已創建，但端口尚未就緒，請稍後檢查${NC}"
                return 0
            fi
        else
            echo -e "${RED}❌ 創建 Qdrant 容器失敗${NC}"
            return 1
        fi
    fi
}

# 函數：啟動 Redis
start_redis() {
    echo -e "${BLUE}=== 啟動 Redis ===${NC}"

    # 檢查 Docker 是否安裝
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}錯誤: Docker 未安裝${NC}"
        echo -e "${YELLOW}請先安裝 Docker Desktop: https://www.docker.com/products/docker-desktop${NC}"
        return 1
    fi

    # 檢查 Docker daemon 是否運行
    if ! docker ps &> /dev/null 2>&1; then
        echo -e "${RED}錯誤: Docker daemon 未運行${NC}"
        echo -e "${YELLOW}請執行以下操作之一：${NC}"
        echo -e "${YELLOW}  1. 啟動 Docker Desktop 應用程式${NC}"
        echo -e "${YELLOW}  2. 或運行: open -a Docker${NC}"
        echo ""

        # 嘗試自動啟動 Docker Desktop (macOS)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo -e "${BLUE}嘗試自動啟動 Docker Desktop...${NC}"
            if open -a Docker 2>/dev/null; then
                echo -e "${GREEN}已嘗試啟動 Docker Desktop，請等待其完全啟動後重新運行此命令${NC}"
                echo -e "${YELLOW}提示: Docker Desktop 通常需要 10-30 秒才能完全啟動${NC}"
            else
                echo -e "${YELLOW}無法自動啟動 Docker Desktop，請手動啟動${NC}"
            fi
        fi

        return 1
    fi

    # 檢查是否使用 docker-compose
    if [ -f "docker-compose.yml" ]; then
        echo -e "${GREEN}發現 docker-compose.yml，使用 docker-compose 管理 Redis${NC}"

        # 偵測 docker-compose 或 docker compose（與 SeaweedFS 一致）
        if command -v docker-compose &> /dev/null; then
            DOCKER_COMPOSE_CMD="docker-compose"
        elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
            DOCKER_COMPOSE_CMD="docker compose"
        else
            echo -e "${RED}❌ 錯誤：未找到 docker-compose 或 docker compose 命令${NC}"
            return 1
        fi

        # 檢查 Redis 容器是否已在運行
        if $DOCKER_COMPOSE_CMD ps redis 2>/dev/null | grep -q "Up"; then
            echo -e "${GREEN}✅ Redis 已在運行 (端口 $REDIS_PORT)${NC}"
            echo -e "${GREEN}   使用 $DOCKER_COMPOSE_CMD 管理: $DOCKER_COMPOSE_CMD ps redis${NC}"
            return 0
        fi

        # 啟動 Redis 容器
        echo -e "${GREEN}啟動 Redis 容器...${NC}"
        if $DOCKER_COMPOSE_CMD up -d redis 2>/dev/null; then
            sleep 3

            # 檢查容器狀態
            if $DOCKER_COMPOSE_CMD ps redis 2>/dev/null | grep -q "Up"; then
                echo -e "${GREEN}✅ Redis 已啟動 (端口 $REDIS_PORT)${NC}"
                echo -e "${GREEN}   使用 $DOCKER_COMPOSE_CMD 管理: $DOCKER_COMPOSE_CMD ps redis${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️  Redis 容器已啟動，但狀態檢查失敗${NC}"
                echo -e "${YELLOW}   請檢查: $DOCKER_COMPOSE_CMD logs redis${NC}"
                return 0
            fi
        else
            echo -e "${RED}❌ 啟動 Redis 容器失敗${NC}"
            echo -e "${YELLOW}   請檢查: $DOCKER_COMPOSE_CMD logs redis${NC}"
            return 1
        fi
    fi

    # 查找 Redis 容器（不使用 docker-compose）
    local container=$(docker ps -a --format '{{.Names}}' | grep -i redis | head -1)
    if [ -n "$container" ]; then
        echo -e "${GREEN}發現 Redis Docker 容器: $container${NC}"

        # 檢查容器是否已在運行
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            echo -e "${GREEN}✅ Redis 已在運行 (端口 $REDIS_PORT)${NC}"
            return 0
        fi

        # 啟動容器
        echo -e "${GREEN}啟動 Redis 容器...${NC}"
        docker start "$container"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 啟動 Redis 容器失敗${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi

        sleep 3

        if check_port $REDIS_PORT; then
            echo -e "${GREEN}✅ Redis 已啟動 (端口 $REDIS_PORT)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  Redis 容器已啟動，但端口尚未就緒${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 0
        fi
    else
        echo -e "${YELLOW}未找到 Redis Docker 容器${NC}"
        echo -e "${BLUE}正在創建 Redis 容器...${NC}"

        if docker run -d             -p $REDIS_PORT:6379             --name redis             redis:7-alpine; then
            echo -e "${GREEN}✅ Redis 容器已創建${NC}"
            sleep 3

            if check_port $REDIS_PORT; then
                echo -e "${GREEN}✅ Redis 已啟動 (端口 $REDIS_PORT)${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ 容器已創建，但端口尚未就緒，請稍後檢查${NC}"
                return 0
            fi
        else
            echo -e "${RED}❌ 創建 Redis 容器失敗${NC}"
            return 1
        fi
    fi
}

# 函數：啟動 FastAPI
start_fastapi() {
    echo -e "${BLUE}=== 啟動 FastAPI ===${NC}"

    kill_port $FASTAPI_PORT "FastAPI"
    kill_process_by_name "api.main"
    kill_process_by_name "uvicorn"

    # 確定 Python 和 uvicorn 路徑
    local PYTHON_CMD="python3"
    local UVICORN_CMD="uvicorn"

    # 檢查虛擬環境
    if [ -d "venv" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
        UVICORN_CMD="venv/bin/uvicorn"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        PYTHON_CMD=".venv/bin/python"
        UVICORN_CMD=".venv/bin/uvicorn"
    fi

    # 檢查 uvicorn 是否安裝
    if ! command -v "$UVICORN_CMD" &> /dev/null && ! "$PYTHON_CMD" -m uvicorn --help &> /dev/null; then
        echo -e "${RED}錯誤: uvicorn 未安裝${NC}"
        echo -e "${YELLOW}請安裝: pip install uvicorn${NC}"
        return 1
    fi

    # 檢查依賴模組
    # 设置 PYTHONPATH 以确保可以导入模块
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
    # 检查模块文件是否存在（不实际导入，避免循环导入问题）
    if [ ! -f "$PROJECT_ROOT/api/main.py" ]; then
        echo -e "${RED}錯誤: FastAPI 主文件不存在${NC}"
        echo -e "${YELLOW}請檢查項目結構是否完整${NC}"
        return 1
    fi
    # 尝试导入（允许失败，因为可能是循环导入问题）
    if ! "$PYTHON_CMD" -c "from api.main import app" 2>/dev/null; then
        echo -e "${YELLOW}警告: 無法導入 FastAPI 應用（可能是循環導入問題）${NC}"
        echo -e "${YELLOW}將嘗試直接啟動服務...${NC}"
    fi

    echo -e "${GREEN}啟動 FastAPI 服務 (端口 $FASTAPI_PORT)...${NC}"
    if command -v "$UVICORN_CMD" &> /dev/null; then
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

        nohup "$UVICORN_CMD" api.main:app \
            --host 0.0.0.0 \
            --port $FASTAPI_PORT \
            --reload \
            > "$LOG_DIR/fastapi.log" 2>&1 &
    else
        nohup "$PYTHON_CMD" -m uvicorn api.main:app \
            --host 0.0.0.0 \
            --port $FASTAPI_PORT \
            --reload \
            > "$LOG_DIR/fastapi.log" 2>&1 &
    fi

    # 等待服務啟動，並重試檢查
    local max_attempts=10
    local attempt=0
    local started=false

    while [ $attempt -lt $max_attempts ]; do
        sleep 1
        if check_port $FASTAPI_PORT; then
            started=true
            break
        fi
        attempt=$((attempt + 1))
    done

    if [ "$started" = true ]; then
        echo -e "${GREEN}✅ FastAPI 已啟動 (端口 $FASTAPI_PORT)${NC}"
        echo -e "${GREEN}   日誌文件: $LOG_DIR/fastapi.log${NC}"
        echo -e "${GREEN}   API 文檔: http://localhost:$FASTAPI_PORT/docs${NC}"
        return 0
    else
        echo -e "${RED}❌ FastAPI 啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: $LOG_DIR/fastapi.log${NC}"
        echo -e "${YELLOW}最後 20 行日誌:${NC}"
        tail -20 "$LOG_DIR/fastapi.log" 2>/dev/null || echo "無法讀取日誌文件"
        return 1
    fi
}

# 函數：啟動 MCP Server
start_mcp_server() {
    echo -e "${BLUE}=== 啟動 MCP Server ===${NC}"

    kill_port $MCP_SERVER_PORT "MCP Server"

    # 確定 Python 路徑
    local PYTHON_CMD="python3"

    # 檢查虛擬環境
    if [ -d "venv" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        PYTHON_CMD=".venv/bin/python"
    fi

    # 檢查 Python 模組
    if ! "$PYTHON_CMD" -c "import mcp.server.main" 2>/dev/null; then
        echo -e "${RED}錯誤: MCP Server 模組未找到${NC}"
        return 1
    fi

    echo -e "${GREEN}啟動 MCP Server (端口 $MCP_SERVER_PORT)...${NC}"
    nohup "$PYTHON_CMD" -m mcp.server.main \
        --host 0.0.0.0 \
        --port $MCP_SERVER_PORT \
        > "$LOG_DIR/mcp_server.log" 2>&1 &

    sleep 3

    if check_port $MCP_SERVER_PORT; then
        echo -e "${GREEN}✅ MCP Server 已啟動 (端口 $MCP_SERVER_PORT)${NC}"
        echo -e "${GREEN}   日誌文件: $LOG_DIR/mcp_server.log${NC}"
        return 0
    else
        echo -e "${RED}❌ MCP Server 啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: $LOG_DIR/mcp_server.log${NC}"
        echo -e "${YELLOW}最後 20 行日誌:${NC}"
        tail -20 "$LOG_DIR/mcp_server.log" 2>/dev/null || echo "無法讀取日誌文件"
        return 1
    fi
}

# 函數：啟動/重啟 Ollama
start_ollama() {
    echo -e "${BLUE}=== Ollama 服務管理 ===${NC}"

    # 檢查 systemd 是否可用
    if ! command -v systemctl &> /dev/null; then
        echo -e "${RED}錯誤: systemctl 未找到，無法管理 Ollama 服務${NC}"
        return 1
    fi

    # 檢查 Ollama 是否已安裝
    if ! command -v ollama &> /dev/null; then
        echo -e "${RED}錯誤: Ollama 未安裝${NC}"
        echo -e "${YELLOW}請安裝: curl -fsSL https://ollama.ai/install.sh | sh${NC}"
        return 1
    fi

    # 檢查服務是否存在
    if ! systemctl is-active --quiet ollama 2>/dev/null; then
        echo -e "${YELLOW}Ollama 服務未運行，正在啟動...${NC}"
        sudo systemctl start ollama
        sleep 3
    else
        echo -e "${GREEN}Ollama 服務已在運行，重啟中...${NC}"
        sudo systemctl restart ollama
        sleep 3
    fi

    # 檢查服務狀態
    if systemctl is-active --quiet ollama; then
        echo -e "${GREEN}✅ Ollama 服務已啟動${NC}"
        echo -e "${GREEN}   API 端口: $OLLAMA_PORT${NC}"
        echo -e "${GREEN}   本地訪問: http://localhost:$OLLAMA_PORT${NC}"

        # 顯示已載入的模型
        echo ""
        echo -e "${BLUE}已安裝的模型:${NC}"
        local models=$(curl -s http://localhost:$OLLAMA_PORT/api/tags 2>/dev/null | python3 -c "import sys,json; [print('  - '+m['name']) for m in json.load(sys.stdin).get('models',[])]" 2>/dev/null)
        if [ -n "$models" ]; then
            echo "$models"
        else
            echo -e "${YELLOW}  無模型或無法獲取模型列表${NC}"
        fi

        # 檢查 GPU
        if command -v nvidia-smi &> /dev/null; then
            echo ""
            echo -e "${BLUE}GPU 狀態:${NC}"
            nvidia-smi --query-gpu=name,memory.used,temperature.gpu,utilization.gpu --format=csv,noheader,nounits 2>/dev/null | while read line; do
                echo -e "  ${GREEN}$line${NC}"
            done
        fi

        return 0
    else
        echo -e "${RED}❌ Ollama 服務啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: sudo journalctl -u ollama -n 20${NC}"
        return 1
    fi
}

# 函數：查看 Ollama 狀態
ollama_status() {
    echo -e "${BLUE}=== Ollama 狀態 ===${NC}"
    echo ""

    # 檢查服務狀態
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet ollama 2>/dev/null; then
            echo -e "${GREEN}✅ Ollama 服務: 運行中${NC}"
            sudo systemctl status ollama --no-pager | head -5
        else
            echo -e "${RED}❌ Ollama 服務: 未運行${NC}"
        fi
    fi

    # 檢查端口
    echo ""
    if check_port $OLLAMA_PORT; then
        echo -e "${GREEN}✅ Ollama API: 監聽中 (端口 $OLLAMA_PORT)${NC}"
    else
        echo -e "${RED}❌ Ollama API: 未監聽 (端口 $OLLAMA_PORT)${NC}"
    fi

    # 顯示模型
    echo ""
    echo -e "${BLUE}已安裝模型:${NC}"
    if curl -s http://localhost:$OLLAMA_PORT/api/tags > /dev/null 2>&1; then
        curl -s http://localhost:$OLLAMA_PORT/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data.get('models', []):
    size_gb = m.get('size', 0) / 1e9
    details = m.get('details', {})
    quant = details.get('quantization_level', 'N/A')
    print(f\"  - {m['name']}: {size_gb:.1f}GB ({quant})\")
" 2>/dev/null || echo -e "${YELLOW}  無法解析模型列表${NC}"
    else
        echo -e "${YELLOW}  無法連接到 Ollama API${NC}"
    fi

    # GPU 狀態
    if command -v nvidia-smi &> /dev/null; then
        echo ""
        echo -e "${BLUE}GPU 監控:${NC}"
        nvidia-smi --query-gpu=name,memory.used,memory.total,temperature.gpu,utilization.gpu,power.draw \
            --format=csv,noheader,nounits 2>/dev/null | while read line; do
            IFS=',' read -r name mem_used mem_total temp util power <<< "$line"
            echo -e "  ${GREEN}$name${NC}"
            echo -e "    顯存: ${mem_used}/${mem_total} MB"
            echo -e "    溫度: ${temp}°C"
            echo -e "    利用率: ${util}%"
            echo -e "    功耗: ${power}W"
        done
    fi
}

# 函數：列出 Ollama 模型
ollama_models() {
    echo -e "${BLUE}=== Ollama 模型列表 ===${NC}"
    echo ""

    if ! check_port $OLLAMA_PORT; then
        echo -e "${RED}❌ Ollama 未運行 (端口 $OLLAMA_PORT)${NC}"
        return 1
    fi

    curl -s http://localhost:$OLLAMA_PORT/api/tags | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f\"總共 {len(data.get('models', []))} 個模型:\\n\")
for m in sorted(data.get('models', []), key=lambda x: x.get('size', 0), reverse=True):
    size_gb = m.get('size', 0) / 1e9
    details = m.get('details', {})
    params = details.get('parameter_size', 'N/A')
    quant = details.get('quantization_level', 'N/A')
    print(f\"{m['name']}\")
    print(f\"  大小: {size_gb:.1f}GB | 參數: {params} | 量化: {quant}\")
    print()
" 2>/dev/null || echo -e "${YELLOW}無法獲取模型列表${NC}"
}

# 函數：啟動前端服務 (Vite)
start_frontend() {
    echo -e "${BLUE}=== 啟動前端服務 (Vite) ===${NC}"

    kill_port $FRONTEND_PORT "Frontend"

    # 檢查前端目錄是否存在
    if [ ! -d "$PROJECT_ROOT/ai-bot" ]; then
        echo -e "${RED}錯誤: 前端目錄不存在${NC}"
        echo -e "${YELLOW}請檢查項目結構是否完整${NC}"
        return 1
    fi

    cd "$PROJECT_ROOT/ai-bot"

    # 檢查 node_modules 是否存在
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}警告: node_modules 不存在，正在安裝依賴...${NC}"
        if command -v pnpm &> /dev/null; then
            pnpm install
        elif command -v npm &> /dev/null; then
            npm install
        else
            echo -e "${RED}錯誤: 未找到 pnpm 或 npm${NC}"
            echo -e "${YELLOW}請安裝 Node.js 和包管理器${NC}"
            return 1
        fi
    fi

    # 檢查 pnpm 或 npm
    local PKG_MANAGER="pnpm"
    if ! command -v pnpm &> /dev/null; then
        if command -v npm &> /dev/null; then
            PKG_MANAGER="npm"
        else
            echo -e "${RED}錯誤: 未找到 pnpm 或 npm${NC}"
            return 1
        fi
    fi

    echo -e "${GREEN}啟動前端服務 (端口 $FRONTEND_PORT)...${NC}"
    nohup $PKG_MANAGER run dev:client > "$LOG_DIR/frontend.log" 2>&1 &

    # 等待服務啟動
    local max_attempts=15
    local attempt=0
    local started=false

    while [ $attempt -lt $max_attempts ]; do
        sleep 1
        if check_port $FRONTEND_PORT; then
            started=true
            break
        fi
        attempt=$((attempt + 1))
    done

    if [ "$started" = true ]; then
        echo -e "${GREEN}✅ 前端服務已啟動 (端口 $FRONTEND_PORT)${NC}"
        echo -e "${GREEN}   日誌文件: $LOG_DIR/frontend.log${NC}"
        echo -e "${GREEN}   本地訪問: http://localhost:$FRONTEND_PORT${NC}"
        return 0
    else
        echo -e "${RED}❌ 前端服務啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: $LOG_DIR/frontend.log${NC}"
        echo -e "${YELLOW}最後 20 行日誌:${NC}"
        tail -20 "$LOG_DIR/frontend.log" 2>/dev/null || echo "無法讀取日誌文件"
        return 1
    fi
}

show_usage() {
    echo -e "${BLUE}AI-Box 服務啟動腳本${NC}"
    echo ""
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  all        啟動所有服務（依賴順序自動啟動）"
    echo ""
    echo "基礎設施:"
    echo "  redis      啟動 Redis"
    echo "  arangodb   啟動 ArangoDB"
    echo "  qdrant     啟動 Qdrant 向量數據庫"
    echo ""
    echo "存儲和監控:"
    echo "  seaweedfs          啟動 SeaweedFS (AI-Box 和 DataLake)
    seaweedfs-ai-box    啟動 AI-Box SeaweedFS
    seaweedfs-datalake  啟動 DataLake SeaweedFS"
    echo "  buckets      創建 SeaweedFS Buckets"
    echo "  monitoring  啟動監控系統 (Prometheus, Grafana, Alertmanager)"
    echo ""
    echo "應用服務:"
    echo "  fastapi|api 啟動 FastAPI (API 服務)"
    echo "  mcp        啟動 MCP Server"
    echo "  frontend   啟動前端服務 (Vite)"
    echo "  worker     啟動 RQ Worker (後台任務處理: kg/vec/file)"
    echo "  mm-worker  啟動 MM-Agent Worker (genai_chat 隊列)"
    echo "  dashboard  啟動 RQ Dashboard (任務監控界面)"
    echo ""
    echo "Ollama (本地 LLM):"
    echo "  ollama           啟動/重啟 Ollama 服務"
    echo "  ollama-status    查看 Ollama 狀態和模型"
    echo "  ollama-restart   重啟 Ollama 服務"
    echo "  ollama-models    列出已安裝模型"
    echo ""
    echo "其他:"
    echo "  status     檢查服務狀態"
    echo "  monitor    實時監控 FastAPI 運行狀態"
    echo "  stop       停止所有服務"
    echo "  help       顯示此幫助信息"
    echo ""
    echo "範例:"
    echo "  $0 all              # 啟動所有服務"
    echo "  $0 qdrant           # 只啟動 Qdrant 向量數據庫"
    echo "  $0 fastapi          # 只啟動 FastAPI
    $0 api              # 同上（別名）"
    echo "  $0 arangodb qdrant  # 啟動 ArangoDB 和 Qdrant"
    echo "  $0 monitoring       # 只啟動監控系統"
}

# 函數：啟動 RQ Worker
start_worker() {
    echo -e "${BLUE}=== 啟動 RQ Worker ===${NC}"

    # 檢查 Redis 是否運行
    if ! check_port $REDIS_PORT; then
        echo -e "${YELLOW}警告: Redis 未運行，Worker 需要 Redis 才能運行${NC}"
        echo -e "${YELLOW}正在啟動 Redis...${NC}"
        start_redis || {
            echo -e "${RED}❌ 無法啟動 Redis，Worker 啟動失敗${NC}"
            return 1
        }
        sleep 2
    fi

    # 檢查 Worker 是否已在運行，如果在運行則先停止
    local worker_pids=$(ps aux | grep -E "rq worker|workers.service" | grep -v grep | awk "{print \$2}")
    if [ -n "$worker_pids" ]; then
        echo -e "${YELLOW}⚠️  RQ Worker 正在運行 (PID: $worker_pids)，先停止...${NC}"
        for pid in $worker_pids; do
            echo -e "${YELLOW}  停止 Worker 進程 $pid...${NC}"
            kill -TERM $pid 2>/dev/null || true
        done
        sleep 2
        # 強制終止仍在運行的 Worker
        local remaining_pids=$(ps aux | grep -E "rq worker|workers.service" | grep -v grep | awk "{print \$2}")
        if [ -n "$remaining_pids" ]; then
            for pid in $remaining_pids; do
                echo -e "${YELLOW}  強制終止 Worker 進程 $pid...${NC}"
                kill -9 $pid 2>/dev/null || true
            done
        fi
        echo -e "${GREEN}✅ RQ Worker 已停止${NC}"
        sleep 1
    fi

    # 確定 Python 路徑
    PYTHON_CMD="python3"
    if [ -d "venv" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        PYTHON_CMD=".venv/bin/python"
    fi

    # 檢查 RQ 是否安裝
    if ! "$PYTHON_CMD" -c "import rq" 2>/dev/null; then
        echo -e "${RED}錯誤: RQ 未安裝${NC}"
        echo -e "${YELLOW}請安裝: pip install rq${NC}"
        return 1
    fi

    # 設置 PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # 啟動 Worker Service（監聽所有隊列，啟用監控）
    echo -e "${GREEN}啟動 RQ Worker Service...${NC}"
    echo -e "${GREEN}  Worker 數量: ${WORKER_NUM:-5}${NC}"
    echo -e "${GREEN} 監聽隊列: kg_extraction, vectorization, file_processing, agent_todo${NC}"
    echo -e "${GREEN} 監控模式: 啟用${NC}"
    echo -e "${GREEN} 日誌文件: $LOG_DIR/worker_service.log${NC}"

    nohup "$PYTHON_CMD" -m workers.service         --queues kg_extraction vectorization file_processing agent_todo         --num-workers ${WORKER_NUM:-5}         --monitor         --check-interval 30         --name rq_worker_ai_box         > "$LOG_DIR/worker_service.log" 2>&1 &

    local worker_pid=$!
    sleep 2

    # 檢查 Worker 是否成功啟動
    if ps -p $worker_pid > /dev/null 2>&1; then
        echo -e "${GREEN}✅ RQ Worker 已啟動 (PID: $worker_pid)${NC}"
        echo -e "${GREEN}  日誌: $LOG_DIR/worker_service.log${NC}"
        echo -e "${YELLOW}  提示: 使用 'tail -f $LOG_DIR/worker_service.log' 查看日誌${NC}"
        return 0
    else
        echo -e "${RED}❌ RQ Worker 啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: $LOG_DIR/worker_service.log${NC}"
        return 1
    fi
}

# 函數：啟動 RQ Dashboard
start_rq_dashboard() {
    echo -e "${BLUE}=== 啟動 RQ Dashboard ===${NC}"

    # 檢查 Redis 是否運行
    if ! check_port $REDIS_PORT; then
        echo -e "${YELLOW}警告: Redis 未運行，Dashboard 需要 Redis 才能運行${NC}"
        echo -e "${YELLOW}正在啟動 Redis...${NC}"
        start_redis || {
            echo -e "${RED}❌ 無法啟動 Redis，Dashboard 啟動失敗${NC}"
            return 1
        }
        sleep 2
    fi

    # Dashboard 端口（可從環境變數讀取）
    DASHBOARD_PORT=${RQ_DASHBOARD_PORT:-9181}

    # 檢查 Dashboard 是否已在運行
    if check_port $DASHBOARD_PORT; then
        local pid=$(lsof -ti :$DASHBOARD_PORT | head -1)
        echo -e "${GREEN}✅ RQ Dashboard 已在運行 (端口 $DASHBOARD_PORT, PID: $pid)${NC}"
        echo -e "${GREEN}  訪問地址: http://localhost:$DASHBOARD_PORT${NC}"
        return 0
    fi

    # 確定 Python 路徑
    PYTHON_CMD="python3"
    if [ -d "venv" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        PYTHON_CMD=".venv/bin/python"
    fi

    # 檢查 rq-dashboard 是否安裝
    if ! "$PYTHON_CMD" -c "import rq_dashboard" 2>/dev/null; then
        echo -e "${RED}錯誤: rq-dashboard 未安裝${NC}"
        echo -e "${YELLOW}請安裝: pip install rq-dashboard${NC}"
        return 1
    fi

    # 設置 PYTHONPATH
    export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

    # 從環境變數讀取 Redis URL
    REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"

    # 啟動 RQ Dashboard
    echo -e "${GREEN}啟動 RQ Dashboard...${NC}"
    echo -e "${GREEN}  Redis URL: $REDIS_URL${NC}"
    echo -e "${GREEN}  端口: $DASHBOARD_PORT${NC}"
    echo -e "${GREEN}  訪問地址: http://localhost:$DASHBOARD_PORT${NC}"

    nohup "$PYTHON_CMD" -m rq_dashboard         --redis-url "$REDIS_URL"         --port "$DASHBOARD_PORT"         > "$LOG_DIR/rq_dashboard.log" 2>&1 &

    local dashboard_pid=$!
    sleep 2

    # 檢查 Dashboard 是否成功啟動
    if check_port $DASHBOARD_PORT; then
        echo -e "${GREEN}✅ RQ Dashboard 已啟動 (端口 $DASHBOARD_PORT, PID: $dashboard_pid)${NC}"
        echo -e "${GREEN}  訪問地址: http://localhost:$DASHBOARD_PORT${NC}"
        echo -e "${GREEN}  日誌: $LOG_DIR/rq_dashboard.log${NC}"
        return 0
    else
        echo -e "${RED}❌ RQ Dashboard 啟動失敗${NC}"
        echo -e "${YELLOW}請檢查日誌: $LOG_DIR/rq_dashboard.log${NC}"
        return 1
    fi
}

# 函數：啟動 AI-Box SeaweedFS（Docker Compose）
start_seaweedfs_ai_box() {
    echo -e "${BLUE}=== 啟動 AI-Box SeaweedFS (Docker Compose) ===${NC}"

    local compose_file="docker-compose.seaweedfs.yml"

    if [ ! -f "$compose_file" ]; then
        echo -e "${YELLOW}⚠️  未找到 $compose_file，跳過 AI-Box SeaweedFS 啟動${NC}"
        return 1
    fi

    echo -e "${BLUE}檢查 AI-Box SeaweedFS 是否已運行...${NC}"

    if check_port $AI_BOX_SEAWEEDFS_S3_PORT; then
        echo -e "${GREEN}✅ AI-Box SeaweedFS 已在運行（端口 $AI_BOX_SEAWEEDFS_S3_PORT）${NC}"
        return 0
    fi

    echo -e "${BLUE}啟動 AI-Box SeaweedFS（Docker Compose）...${NC}"

    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ 錯誤：未找到 docker-compose 或 docker compose 命令${NC}"
        return 1
    fi

    # 僅使用當前 compose 檔，避免載入根目錄 docker-compose.yml（消除 version 警告）
    COMPOSE_FILE="$compose_file" $DOCKER_COMPOSE_CMD -f "$compose_file" up -d

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ AI-Box SeaweedFS 啟動失敗${NC}"
        return 1
    fi

    echo -e "${BLUE}等待 AI-Box SeaweedFS 啟動...${NC}"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if check_port $AI_BOX_SEAWEEDFS_S3_PORT; then
            echo -e "${GREEN}✅ AI-Box SeaweedFS 啟動成功（端口 $AI_BOX_SEAWEEDFS_S3_PORT）${NC}"
            sleep 2
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
        echo -e "${YELLOW}  等待中... ($attempt/$max_attempts)${NC}"
    done

    echo -e "${RED}❌ AI-Box SeaweedFS 啟動超時${NC}"
    return 1
}

# 函數：啟動 DataLake SeaweedFS（Docker Compose）
start_seaweedfs_datalake() {
    echo -e "${BLUE}=== 啟動 DataLake SeaweedFS (Docker Compose) ===${NC}"

    local compose_file="docker-compose.seaweedfs-datalake.yml"

    if [ ! -f "$compose_file" ]; then
        echo -e "${YELLOW}⚠️  未找到 $compose_file，跳過 DataLake SeaweedFS 啟動${NC}"
        return 1
    fi

    echo -e "${BLUE}檢查 DataLake SeaweedFS 是否已運行...${NC}"

    if check_port $DATALAKE_SEAWEEDFS_S3_PORT; then
        echo -e "${GREEN}✅ DataLake SeaweedFS 已在運行（端口 $DATALAKE_SEAWEEDFS_S3_PORT）${NC}"
        return 0
    fi

    echo -e "${BLUE}啟動 DataLake SeaweedFS（Docker Compose）...${NC}"

    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ 錯誤：未找到 docker-compose 或 docker compose 命令${NC}"
        return 1
    fi

    # 僅使用當前 compose 檔，避免載入根目錄 docker-compose.yml（消除 version 警告）
    COMPOSE_FILE="$compose_file" $DOCKER_COMPOSE_CMD -f "$compose_file" up -d

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ DataLake SeaweedFS 啟動失敗${NC}"
        return 1
    fi

    echo -e "${BLUE}等待 DataLake SeaweedFS 啟動...${NC}"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if check_port $DATALAKE_SEAWEEDFS_S3_PORT; then
            echo -e "${GREEN}✅ DataLake SeaweedFS 啟動成功（端口 $DATALAKE_SEAWEEDFS_S3_PORT）${NC}"
            sleep 2
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
        echo -e "${YELLOW}  等待中... ($attempt/$max_attempts)${NC}"
    done

    echo -e "${RED}❌ DataLake SeaweedFS 啟動超時${NC}"
    return 1
}

# 函數：啟動所有 SeaweedFS 服務（兼容舊版本）
start_seaweedfs_docker() {
    echo -e "${BLUE}=== 啟動 SeaweedFS 服務（AI-Box 和 DataLake） ===${NC}"
    start_seaweedfs_ai_box || true
    start_seaweedfs_datalake || true
}

# 函數：啟動監控系統（Prometheus、Grafana、Alertmanager、Exporter）
start_monitoring() {
    echo -e "${BLUE}=== 啟動監控系統 ===${NC}"

    local compose_file="docker-compose.monitoring.yml"

    if [ ! -f "$compose_file" ]; then
        echo -e "${YELLOW}⚠️  未找到 $compose_file，跳過監控系統啟動${NC}"
        return 1
    fi

    echo -e "${BLUE}檢查監控系統是否已運行...${NC}"

    # 檢查 Grafana 是否已運行
    if check_port 3001; then
        echo -e "${GREEN}✅ 監控系統已在運行（Grafana 端口 3001）${NC}"
        return 0
    fi

    echo -e "${BLUE}啟動監控系統（Docker Compose）...${NC}"

    if command -v docker-compose &> /dev/null; then
        DOCKER_COMPOSE_CMD="docker-compose"
    elif command -v docker &> /dev/null && docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE_CMD="docker compose"
    else
        echo -e "${RED}❌ 錯誤：未找到 docker-compose 或 docker compose 命令${NC}"
        return 1
    fi

    # 僅使用當前 compose 檔，避免載入根目錄 docker-compose.yml（消除 version 警告）
    COMPOSE_FILE="$compose_file" $DOCKER_COMPOSE_CMD -f "$compose_file" up -d

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 監控系統啟動失敗${NC}"
        return 1
    fi

    echo -e "${BLUE}等待監控系統啟動...${NC}"
    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if check_port 3001; then
            echo -e "${GREEN}✅ 監控系統啟動成功${NC}"
            echo -e "${GREEN}   Grafana: http://localhost:3001${NC}"
            echo -e "${GREEN}   Prometheus: http://localhost:9090${NC}"
            echo -e "${GREEN}   Alertmanager: http://localhost:9093${NC}"
            sleep 2
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
        echo -e "${YELLOW}  等待中... ($attempt/$max_attempts)${NC}"
    done

    echo -e "${RED}❌ 監控系統啟動超時${NC}"
    return 1
}

# 函數：創建 SeaweedFS Buckets
create_seaweedfs_buckets() {
    echo -e "${BLUE}=== 創建 SeaweedFS Buckets ===${NC}"

    local script_path="scripts/migration/create_seaweedfs_buckets.py"

    if [ ! -f "$script_path" ]; then
        echo -e "${YELLOW}⚠️  未找到 $script_path，跳過 Buckets 創建${NC}"
        return 1
    fi

    # 檢查是否配置了 SeaweedFS 環境變數
    if [ -z "$AI_BOX_SEAWEEDFS_S3_ENDPOINT" ] && [ -z "$DATALAKE_SEAWEEDFS_S3_ENDPOINT" ]; then
        echo -e "${YELLOW}⚠️  未配置 SeaweedFS 環境變數，跳過 Buckets 創建${NC}"
        echo -e "${YELLOW}提示: 如需使用 SeaweedFS，請在 .env 文件中配置相關環境變數${NC}"
        return 1
    fi

    echo -e "${BLUE}創建 SeaweedFS Buckets...${NC}"

    # 確定 Python 路徑
    PYTHON_CMD="python3"
    if [ -d "venv" ]; then
        source venv/bin/activate
        PYTHON_CMD="venv/bin/python"
    elif [ -d ".venv" ]; then
        source .venv/bin/activate
        PYTHON_CMD=".venv/bin/python"
    fi

    # 運行 Buckets 創建腳本
    if "$PYTHON_CMD" "$script_path" --service all; then
        echo -e "${GREEN}✅ SeaweedFS Buckets 創建成功${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  SeaweedFS Buckets 創建失敗或已存在${NC}"
        return 1
    fi
}
# 函數：檢查服務狀態
check_status() {
    echo -e "${BLUE}=== 服務狀態檢查 ===${NC}"
    echo ""

    # 檢查 Ollama 狀態
    echo -e "${BLUE}Ollama (本地 LLM):${NC}"
    if command -v systemctl &> /dev/null; then
        if systemctl is-active --quiet ollama 2>/dev/null; then
            local ollama_pid=$(ps aux | grep "[o]llama serve" | awk '{print $2}' | head -1)
            if [ -n "$ollama_pid" ]; then
                echo -e "${GREEN}✅ Ollama 服務${NC} - 運行中 (PID: $ollama_pid)"
            else
                echo -e "${GREEN}✅ Ollama 服務${NC} - 運行中"
            fi

            # 顯示已載入的模型數量
            local model_count=$(curl -s http://localhost:$OLLAMA_PORT/api/tags 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "0")
            echo -e "${GREEN}   已安裝模型: ${model_count} 個${NC}"
            echo -e "${GREEN}   API: http://localhost:$OLLAMA_PORT${NC}"

            # GPU 狀態
            if command -v nvidia-smi &> /dev/null; then
                local gpu_info=$(nvidia-smi --query-gpu=name,utilization.gpu,temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
                if [ -n "$gpu_info" ]; then
                    echo -e "${GREEN}   GPU: $gpu_info${NC}"
                fi
            fi
        else
            echo -e "${RED}❌ Ollama 服務${NC} - 未運行"
            echo -e "${YELLOW}   提示: 運行 '$0 ollama' 啟動${NC}"
        fi
    else
        # 非 systemd 系統，直接檢查端口
        if check_port $OLLAMA_PORT; then
            local ollama_pid=$(ps aux | grep "[o]llama serve" | awk '{print $2}' | head -1)
            echo -e "${GREEN}✅ Ollama${NC} - 運行中 (端口 $OLLAMA_PORT, PID: $ollama_pid)"
        else
            echo -e "${RED}❌ Ollama${NC} - 未運行 (端口 $OLLAMA_PORT)"
        fi
    fi
    echo ""

    services=(
        "Qdrant:$QDRANT_REST_PORT"
        "ArangoDB:$ARANGODB_PORT"
        "Redis:$REDIS_PORT"
        "FastAPI:$FASTAPI_PORT"
        "MCP Server:$MCP_SERVER_PORT"
        "Frontend:$FRONTEND_PORT"
    )

    # 檢查 Worker 狀態
    echo -e "${BLUE}Worker 狀態:${NC}"
    local worker_pids=$(ps aux | grep -E "rq worker|workers.service" | grep -v grep | awk "{print \$2}")
    if [ -n "$worker_pids" ]; then
        # 將多個 PID 用逗號分隔，避免換行
        local formatted_pids=$(echo "$worker_pids" | tr '
' ' ' | sed 's/ $//')
        echo -e "${GREEN}✅ RQ Worker${NC} - 運行中 (PID: $formatted_pids)"
    else
        echo -e "${RED}❌ RQ Worker${NC} - 未運行"
    fi
    # 檢查 Dashboard 狀態
    echo -e "${BLUE}Dashboard 狀態:${NC}"
    local dashboard_port=${RQ_DASHBOARD_PORT:-9181}
    if check_port $dashboard_port; then
        local dashboard_pid=$(lsof -ti :$dashboard_port | head -1)
        echo -e "${GREEN}✅ RQ Dashboard${NC} - 運行中 (端口 $dashboard_port, PID: $dashboard_pid)"
        echo -e "${GREEN}  訪問地址: http://localhost:$dashboard_port${NC}"
    else
        echo -e "${RED}❌ RQ Dashboard${NC} - 未運行 (端口 $dashboard_port)"
    fi

    # 檢查 Qdrant 狀態
    echo -e "${BLUE}向量數據庫狀態:${NC}"
    if check_port $QDRANT_REST_PORT; then
        local qdrant_pid=$(lsof -ti :$QDRANT_REST_PORT | head -1)
        echo -e "${GREEN}✅ Qdrant${NC} - 運行中 (端口 $QDRANT_REST_PORT, PID: $qdrant_pid)"
        echo -e "${GREEN}   Dashboard: http://localhost:$QDRANT_REST_PORT/dashboard${NC}"
    else
        echo -e "${RED}❌ Qdrant${NC} - 未運行 (端口 $QDRANT_REST_PORT)"
        echo -e "${YELLOW}   提示: 請運行 'start_qdrant' 啟動${NC}"
    fi

    # 檢查 SeaweedFS 狀態（改進版 - 分別檢查 Master、Volume、Filer）
    echo -e "${BLUE}SeaweedFS 狀態:${NC}"

    # 檢查 AI-Box SeaweedFS
    echo -e "${BLUE}  AI-Box SeaweedFS:${NC}"
    # 檢查 Master
    if check_port $AI_BOX_SEAWEEDFS_MASTER_PORT; then
        echo -e "${GREEN}    ✅ Master${NC} - 運行中 (端口 $AI_BOX_SEAWEEDFS_MASTER_PORT)"
    else
        echo -e "${RED}    ❌ Master${NC} - 未運行 (端口 $AI_BOX_SEAWEEDFS_MASTER_PORT)"
    fi
    # 檢查 Volume（通過 Docker 容器狀態）
    if docker ps --format "{{.Names}}" --filter "name=seaweedfs-ai-box-volume" 2>/dev/null | grep -q "seaweedfs-ai-box-volume"; then
        local volume_status=$(docker ps --format "{{.Status}}" --filter "name=seaweedfs-ai-box-volume" 2>/dev/null | head -1)
        echo -e "${GREEN}    ✅ Volume${NC} - 運行中 ($volume_status)"
    else
        echo -e "${RED}    ❌ Volume${NC} - 未運行"
    fi
    # 檢查 Filer API
    if check_port $AI_BOX_SEAWEEDFS_FILER_PORT; then
        echo -e "${GREEN}    ✅ Filer API${NC} - 運行中 (端口 $AI_BOX_SEAWEEDFS_FILER_PORT)"
    else
        echo -e "${RED}    ❌ Filer API${NC} - 未運行 (端口 $AI_BOX_SEAWEEDFS_FILER_PORT)"
    fi
    # 檢查 S3 API
    if check_port $AI_BOX_SEAWEEDFS_S3_PORT; then
        echo -e "${GREEN}    ✅ S3 API${NC} - 運行中 (端口 $AI_BOX_SEAWEEDFS_S3_PORT)"
    else
        echo -e "${RED}    ❌ S3 API${NC} - 未運行 (端口 $AI_BOX_SEAWEEDFS_S3_PORT)"
    fi

    # 檢查 DataLake SeaweedFS
    echo -e "${BLUE}  DataLake SeaweedFS:${NC}"
    # 檢查 Master
    if check_port $DATALAKE_SEAWEEDFS_MASTER_PORT; then
        echo -e "${GREEN}    ✅ Master${NC} - 運行中 (端口 $DATALAKE_SEAWEEDFS_MASTER_PORT)"
    else
        echo -e "${RED}    ❌ Master${NC} - 未運行 (端口 $DATALAKE_SEAWEEDFS_MASTER_PORT)"
    fi
    # 檢查 Volume（通過 Docker 容器狀態）
    if docker ps --format "{{.Names}}" --filter "name=seaweedfs-datalake-volume" 2>/dev/null | grep -q "seaweedfs-datalake-volume"; then
        local volume_status=$(docker ps --format "{{.Status}}" --filter "name=seaweedfs-datalake-volume" 2>/dev/null | head -1)
        echo -e "${GREEN}    ✅ Volume${NC} - 運行中 ($volume_status)"
    else
        echo -e "${RED}    ❌ Volume${NC} - 未運行"
    fi
    # 檢查 Filer API
    if check_port $DATALAKE_SEAWEEDFS_FILER_PORT; then
        echo -e "${GREEN}    ✅ Filer API${NC} - 運行中 (端口 $DATALAKE_SEAWEEDFS_FILER_PORT)"
    else
        echo -e "${RED}    ❌ Filer API${NC} - 未運行 (端口 $DATALAKE_SEAWEEDFS_FILER_PORT)"
    fi
    # 檢查 S3 API
    if check_port $DATALAKE_SEAWEEDFS_S3_PORT; then
        echo -e "${GREEN}    ✅ S3 API${NC} - 運行中 (端口 $DATALAKE_SEAWEEDFS_S3_PORT)"
    else
        echo -e "${RED}    ❌ S3 API${NC} - 未運行 (端口 $DATALAKE_SEAWEEDFS_S3_PORT)"
    fi

    # 檢查監控系統狀態
    echo -e "${BLUE}監控系統狀態:${NC}"
    # 檢查 Grafana
    if check_port 3001; then
        local grafana_pid=$(lsof -ti :3001 | head -1)
        echo -e "${GREEN}  ✅ Grafana${NC} - 運行中 (端口 3001, PID: $grafana_pid)"
        echo -e "${GREEN}     訪問地址: http://localhost:3001${NC}"
    else
        echo -e "${RED}  ❌ Grafana${NC} - 未運行 (端口 3001)"
    fi
    # 檢查 Prometheus
    if check_port 9090; then
        local prometheus_pid=$(lsof -ti :9090 | head -1)
        echo -e "${GREEN}  ✅ Prometheus${NC} - 運行中 (端口 9090, PID: $prometheus_pid)"
        echo -e "${GREEN}     訪問地址: http://localhost:9090${NC}"
    else
        echo -e "${RED}  ❌ Prometheus${NC} - 未運行 (端口 9090)"
    fi
    # 檢查 Alertmanager
    if check_port 9093; then
        local alertmanager_pid=$(lsof -ti :9093 | head -1)
        echo -e "${GREEN}  ✅ Alertmanager${NC} - 運行中 (端口 9093, PID: $alertmanager_pid)"
        echo -e "${GREEN}     訪問地址: http://localhost:9093${NC}"
    else
        echo -e "${RED}  ❌ Alertmanager${NC} - 未運行 (端口 9093)"
    fi
    # 檢查 Node Exporter
    if check_port 9100; then
        echo -e "${GREEN}  ✅ Node Exporter${NC} - 運行中 (端口 9100)"
    else
        echo -e "${RED}  ❌ Node Exporter${NC} - 未運行 (端口 9100)"
    fi
    # 檢查 Redis Exporter
    if check_port 9121; then
        echo -e "${GREEN}  ✅ Redis Exporter${NC} - 運行中 (端口 9121)"
    else
        echo -e "${RED}  ❌ Redis Exporter${NC} - 未運行 (端口 9121)"
    fi


    for service_info in "${services[@]}"; do
        IFS=':' read -r name port <<< "$service_info"
        if check_port $port; then
            local pid=$(lsof -ti :$port | head -1)
            echo -e "${GREEN}✅ $name${NC} - 運行中 (端口 $port, PID: $pid)"
        else
            echo -e "${RED}❌ $name${NC} - 未運行 (端口 $port)"
        fi
    done
}

# 函數：實時監控 FastAPI 運行狀態
monitor_fastapi() {
    echo -e "${BLUE}=== FastAPI 實時監控 ===${NC}"
    echo -e "${YELLOW}按 Ctrl+C 退出監控${NC}"
    echo ""

    local FASTAPI_URL="http://localhost:$FASTAPI_PORT"
    local LOG_FILE="$LOG_DIR/fastapi.log"
    local UPDATE_INTERVAL=2  # 更新間隔（秒）

    # 檢查 FastAPI 是否運行
    if ! check_port $FASTAPI_PORT; then
        echo -e "${RED}❌ FastAPI 未運行 (端口 $FASTAPI_PORT)${NC}"
        echo -e "${YELLOW}請先啟動 FastAPI: $0 fastapi${NC}"
        return 1
    fi

    # 獲取進程 PID
    local pid=$(lsof -ti :$FASTAPI_PORT | head -1)
    if [ -z "$pid" ]; then
        echo -e "${RED}❌ 無法獲取 FastAPI 進程 ID${NC}"
        return 1
    fi

    echo -e "${GREEN}✅ FastAPI 運行中 (PID: $pid, 端口: $FASTAPI_PORT)${NC}"
    echo ""

    # 監控循環
    while true; do
        clear
        echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║          FastAPI 實時監控 - $(date '+%Y-%m-%d %H:%M:%S')          ║${NC}"
        echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""

        # 1. 進程狀態
        echo -e "${YELLOW}📊 進程狀態:${NC}"
        if ps -p $pid > /dev/null 2>&1; then
            local cpu=$(ps -p $pid -o %cpu= | tr -d ' ')
            local mem=$(ps -p $pid -o %mem= | tr -d ' ')
            local vsz=$(ps -p $pid -o vsz= | tr -d ' ')
            local rss=$(ps -p $pid -o rss= | tr -d ' ')
            local mem_mb=$((rss / 1024))
            local vsz_mb=$((vsz / 1024))

            echo -e "  PID: ${GREEN}$pid${NC}"
            echo -e "  CPU 使用率: ${GREEN}${cpu}%${NC}"
            echo -e "  內存使用率: ${GREEN}${mem}%${NC}"
            echo -e "  虛擬內存: ${GREEN}${vsz_mb} MB${NC}"
            echo -e "  實際內存: ${GREEN}${mem_mb} MB${NC}"
        else
            echo -e "  ${RED}❌ 進程不存在${NC}"
            break
        fi
        echo ""

        # 2. 端口狀態
        echo -e "${YELLOW}🔌 端口狀態:${NC}"
        if check_port $FASTAPI_PORT; then
            echo -e "  端口 $FASTAPI_PORT: ${GREEN}✅ 監聽中${NC}"
        else
            echo -e "  端口 $FASTAPI_PORT: ${RED}❌ 未監聽${NC}"
        fi
        echo ""

        # 3. 健康檢查
        echo -e "${YELLOW}🏥 健康檢查:${NC}"
        local health_response=$(curl -s -w "
%{http_code}" --max-time 2 "$FASTAPI_URL/api/v1/health" 2>/dev/null || echo -e "
000")
        local health_code=$(echo "$health_response" | tail -1)
        if [ "$health_code" = "200" ]; then
            echo -e "  API 端點: ${GREEN}✅ 正常 (HTTP $health_code)${NC}"
        elif [ "$health_code" = "404" ]; then
            echo -e "  API 端點: ${YELLOW}⚠️  端點不存在 (HTTP $health_code)${NC}"
        elif [ "$health_code" = "000" ]; then
            echo -e "  API 端點: ${RED}❌ 無法連接${NC}"
        else
            echo -e "  API 端點: ${YELLOW}⚠️  HTTP $health_code${NC}"
        fi

        # 測試登錄端點
        local login_response=$(curl -s -w "
%{http_code}" --max-time 2 -X POST "$FASTAPI_URL/api/v1/auth/login" \
            -H "Content-Type: application/json" \
            -d '{"username":"test","password":"test"}' 2>/dev/null || echo -e "
000")
        local login_code=$(echo "$login_response" | tail -1)
        if [ "$login_code" = "200" ] || [ "$login_code" = "401" ]; then
            echo -e "  登錄端點: ${GREEN}✅ 響應正常 (HTTP $login_code)${NC}"
        elif [ "$login_code" = "000" ]; then
            echo -e "  登錄端點: ${RED}❌ 無法連接${NC}"
        else
            echo -e "  登錄端點: ${YELLOW}⚠️  HTTP $login_code${NC}"
        fi
        echo ""

        # 4. 日誌統計
        echo -e "${YELLOW}📝 日誌統計 (最近 100 行):${NC}"
        if [ -f "$LOG_FILE" ]; then
            local total_lines=$(wc -l < "$LOG_FILE" 2>/dev/null || echo "0")
            local error_count=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -i "ERROR\|Exception\|Traceback" | wc -l | tr -d ' ')
            local warn_count=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -i "WARNING\|WARN" | wc -l | tr -d ' ')
            local info_count=$(tail -100 "$LOG_FILE" 2>/dev/null | grep -i "INFO" | wc -l | tr -d ' ')

            echo -e "  總日誌行數: ${GREEN}$total_lines${NC}"
            echo -e "  錯誤數量: ${RED}$error_count${NC}"
            echo -e "  警告數量: ${YELLOW}$warn_count${NC}"
            echo -e "  信息數量: ${GREEN}$info_count${NC}"
        else
            echo -e "  ${RED}❌ 日誌文件不存在: $LOG_FILE${NC}"
        fi
        echo ""

        # 5. 最近的錯誤（如果有）
        if [ -f "$LOG_FILE" ] && [ "$error_count" -gt 0 ]; then
            echo -e "${YELLOW}⚠️  最近的錯誤 (最後 3 條):${NC}"
            tail -100 "$LOG_FILE" 2>/dev/null | grep -i "ERROR\|Exception\|Traceback" | tail -3 | while IFS= read -r line; do
                echo -e "  ${RED}$line${NC}" | cut -c1-80
            done
            echo ""
        fi

        # 6. 最近的日誌（最後 5 行）
        echo -e "${YELLOW}📋 最近的日誌 (最後 5 行):${NC}"
        if [ -f "$LOG_FILE" ]; then
            tail -5 "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
                if echo "$line" | grep -qi "ERROR\|Exception"; then
                    echo -e "  ${RED}$line${NC}" | cut -c1-80
                elif echo "$line" | grep -qi "WARNING\|WARN"; then
                    echo -e "  ${YELLOW}$line${NC}" | cut -c1-80
                else
                    echo -e "  ${GREEN}$line${NC}" | cut -c1-80
                fi
            done
        fi
        echo ""

        # 7. 系統資源
        echo -e "${YELLOW}💻 系統資源:${NC}"
        local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ',')
        echo -e "  系統負載: ${GREEN}$load_avg${NC}"
        echo ""

        echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}更新間隔: ${UPDATE_INTERVAL} 秒 | 按 Ctrl+C 退出${NC}"

        sleep $UPDATE_INTERVAL
    done
}

# 函數：停止所有服務
stop_all() {
    echo -e "${BLUE}=== 停止所有服務 ===${NC}"

    ports=($QDRANT_REST_PORT $ARANGODB_PORT $CHROMADB_PORT $REDIS_PORT $FASTAPI_PORT $MCP_SERVER_PORT $FRONTEND_PORT)
    service_names=("Qdrant" "ArangoDB" "ChromaDB" "Redis" "FastAPI" "MCP Server" "Frontend")

    for i in "${!ports[@]}"; do
        port=${ports[$i]}
        name=${service_names[$i]}
        if check_port $port; then
            echo -e "${YELLOW}停止 $name (端口 $port)...${NC}"
            kill_port $port "$name"
        fi
    done

    # 停止 Worker
    echo -e "${YELLOW}停止 RQ Worker...${NC}"
    local worker_pids=$(ps aux | grep -E "rq worker|workers.service" | grep -v grep | awk "{print \$2}")
    if [ -n "$worker_pids" ]; then
        for pid in $worker_pids; do
            echo -e "${YELLOW}  停止 Worker 進程 $pid...${NC}"
            kill -TERM $pid 2>/dev/null || true
        done
        sleep 2
        # 強制終止仍在運行的 Worker
        local remaining_pids=$(ps aux | grep -E "rq worker|workers.service" | grep -v grep | awk "{print \$2}")
        if [ -n "$remaining_pids" ]; then
            for pid in $remaining_pids; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
    fi
    # 停止 Dashboard
    echo -e "${YELLOW}停止 RQ Dashboard...${NC}"
    local dashboard_port=${RQ_DASHBOARD_PORT:-9181}
    if check_port $dashboard_port; then
        local dashboard_pids=$(lsof -ti :$dashboard_port)
        if [ -n "$dashboard_pids" ]; then
            for pid in $dashboard_pids; do
                echo -e "${YELLOW}  停止 Dashboard 進程 $pid...${NC}"
                kill -TERM $pid 2>/dev/null || true
            done
            sleep 1
            # 強制終止仍在運行的 Dashboard
            local remaining_pids=$(lsof -ti :$dashboard_port 2>/dev/null)
            if [ -n "$remaining_pids" ]; then
                for pid in $remaining_pids; do
                    kill -9 $pid 2>/dev/null || true
                done
            fi
        fi
    fi
    echo -e "${GREEN}✅ 所有服務已停止${NC}"
}

# 主邏輯
main() {
    if [ $# -eq 0 ]; then
        show_usage
        exit 0
    fi

    # 處理多個參數
    for arg in "$@"; do
        case "$arg" in
            all)
                echo -e "${BLUE}=== 啟動所有服務 ===${NC}"
                echo ""
                echo -e "${BLUE}[1/3] 啟動基礎設施服務...${NC}"
                start_redis || true
                start_arangodb || true
                start_qdrant || true
                echo ""
                echo -e "${BLUE}[2/3] 啟動存儲和監控服務...${NC}"
                start_seaweedfs_docker || true
                create_seaweedfs_buckets || true
                start_monitoring || true
                echo ""
                echo -e "${BLUE}[3/3] 啟動應用服務...${NC}"
                start_fastapi || true
                start_mcp || true
                start_frontend || true
                start_worker || true
                start_rq_dashboard || true
                echo ""
                echo -e "${GREEN}=== 啟動完成 ===${NC}"
                check_status
                ;;
            qdrant)
                start_qdrant
                ;;
            arangodb)
                start_arangodb
                ;;
            redis)
                start_redis
                ;;
            fastapi|api)
                start_fastapi
                ;;
            mcp)
                start_mcp_server
                ;;
            frontend)
                start_frontend
                ;;
            worker)
                start_worker
                ;;
            dashboard)
                start_rq_dashboard
                ;;
            monitoring)
                start_monitoring
                ;;
            seaweedfs)
                start_seaweedfs_docker
                ;;
            seaweedfs-ai-box)
                start_seaweedfs_ai_box
                ;;
            seaweedfs-datalake)
                start_seaweedfs_datalake
                ;;
            buckets)
                create_seaweedfs_buckets
                ;;
            ollama)
                start_ollama
                ;;
            ollama-status|ollama_status)
                ollama_status
                ;;
            ollama-models|ollama_models)
                ollama_models
                ;;
            ollama-restart|ollama_restart)
                echo -e "${BLUE}=== 重啟 Ollama ===${NC}"
                if command -v systemctl &> /dev/null; then
                    sudo systemctl restart ollama
                    sleep 3
                    if systemctl is-active --quiet ollama; then
                        echo -e "${GREEN}✅ Ollama 已重啟${NC}"
                        ollama_status
                    else
                        echo -e "${RED}❌ Ollama 重啟失敗${NC}"
                    fi
                else
                    echo -e "${RED}錯誤: systemctl 未找到${NC}"
                fi
                ;;
            status)
                check_status
                ;;
            monitor)
                monitor_fastapi
                ;;
            stop)
                stop_all
                ;;
            help|--help|-h)
                show_usage
                ;;
            *)
                echo -e "${RED}錯誤: 未知選項 '$arg'${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
}

# 執行主函數
main "$@"
