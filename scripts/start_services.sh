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
# 最後修改日期: 2025-01-27

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 服務配置
ARANGODB_PORT=8529
CHROMADB_PORT=8001
FASTAPI_PORT=8000
MCP_SERVER_PORT=8002

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日誌目錄
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 函數：檢查端口是否被占用
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # 端口被占用
    else
        return 1  # 端口未被占用
    fi
}

# 函數：關閉占用端口的進程
kill_port() {
    local port=$1
    local service_name=$2

    if check_port $port; then
        echo -e "${YELLOW}檢測到端口 $port 已被占用，正在關閉...${NC}"
        local pids=$(lsof -ti :$port)
        if [ -n "$pids" ]; then
            for pid in $pids; do
                local proc_name=$(ps -p $pid -o comm= 2>/dev/null || echo "unknown")
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
                echo -e "${RED}  警告: 端口 $port 仍被占用 (PID: $remaining_pids)${NC}"
                echo -e "${YELLOW}  嘗試強制關閉...${NC}"
                for pid in $remaining_pids; do
                    kill -9 $pid 2>/dev/null || true
                done
                sleep 1
                if check_port $port; then
                    echo -e "${RED}  錯誤: 無法釋放端口 $port${NC}"
                    return 1
                fi
            fi
            echo -e "${GREEN}  端口 $port 已釋放${NC}"
        fi
    fi
    return 0
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


# 函數：啟動 ChromaDB
start_chromadb() {
    echo -e "${BLUE}=== 啟動 ChromaDB ===${NC}"

    kill_port $CHROMADB_PORT "ChromaDB"

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

    # 查找 ChromaDB 容器
    local container=$(docker ps -a --format '{{.Names}}' | grep -i chroma | head -1)
    if [ -n "$container" ]; then
        echo -e "${GREEN}發現 ChromaDB Docker 容器: $container${NC}"

        # 檢查容器是否已在運行
        if docker ps --format '{{.Names}}' | grep -q "^${container}$"; then
            echo -e "${GREEN}✅ ChromaDB 已在運行 (端口 $CHROMADB_PORT)${NC}"
            echo -e "${GREEN}   API: http://localhost:$CHROMADB_PORT${NC}"
            return 0
        fi

        # 啟動容器
        echo -e "${GREEN}啟動 ChromaDB 容器...${NC}"
        docker start "$container"

        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ 啟動 ChromaDB 容器失敗${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi

        sleep 5

        if check_port $CHROMADB_PORT; then
            echo -e "${GREEN}✅ ChromaDB 已啟動 (端口 $CHROMADB_PORT)${NC}"
            echo -e "${GREEN}   API: http://localhost:$CHROMADB_PORT${NC}"
            return 0
        else
            echo -e "${RED}❌ ChromaDB 啟動失敗（端口未監聽）${NC}"
            echo -e "${YELLOW}請檢查日誌: docker logs $container${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}未找到 ChromaDB Docker 容器${NC}"
        echo -e "${BLUE}正在創建 ChromaDB 容器...${NC}"

        # 從環境變數獲取配置
        CHROMADB_PERSIST_DIR=${CHROMADB_PERSIST_DIR:-"./chroma_data"}

        # 創建持久化目錄（如果不存在）
        mkdir -p "$CHROMADB_PERSIST_DIR"

        if docker run -d \
            -p $CHROMADB_PORT:8000 \
            -v "$(pwd)/$CHROMADB_PERSIST_DIR:/chroma/chroma" \
            --name chromadb \
            chromadb/chroma:latest; then
            echo -e "${GREEN}✅ ChromaDB 容器已創建${NC}"
            echo -e "${GREEN}   持久化目錄: $CHROMADB_PERSIST_DIR${NC}"
            sleep 5

            if check_port $CHROMADB_PORT; then
                echo -e "${GREEN}✅ ChromaDB 已啟動 (端口 $CHROMADB_PORT)${NC}"
                echo -e "${GREEN}   API: http://localhost:$CHROMADB_PORT${NC}"
                return 0
            else
                echo -e "${YELLOW}⚠️ 容器已創建，但端口尚未就緒，請稍後檢查${NC}"
                return 0
            fi
        else
            echo -e "${RED}❌ 創建 ChromaDB 容器失敗${NC}"
            return 1
        fi
    fi
}


# 函數：啟動 FastAPI
start_fastapi() {
    echo -e "${BLUE}=== 啟動 FastAPI ===${NC}"

    kill_port $FASTAPI_PORT "FastAPI"

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
        echo -e "${RED}錯誤: 無法導入 FastAPI 應用${NC}"
        echo -e "${YELLOW}請檢查依賴是否安裝完整${NC}"
        echo -e "${YELLOW}嘗試: pip install -r requirements.txt${NC}"
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

# 函數：顯示使用說明
show_usage() {
    echo -e "${BLUE}AI-Box 服務啟動腳本${NC}"
    echo ""
    echo "用法: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  all        啟動所有服務 (ArangoDB, ChromaDB, FastAPI)"
    echo "  arangodb   啟動 ArangoDB"
    echo "  chromadb   啟動 ChromaDB"
    echo "  fastapi    啟動 FastAPI"
    echo "  mcp        啟動 MCP Server"
    echo "  status     檢查服務狀態"
    echo "  stop       停止所有服務"
    echo "  help       顯示此幫助信息"
    echo ""
    echo "範例:"
    echo "  $0 all              # 啟動所有服務"
    echo "  $0 fastapi          # 只啟動 FastAPI"
    echo "  $0 arangodb chromadb # 啟動 ArangoDB 和 ChromaDB"
}

# 函數：檢查服務狀態
check_status() {
    echo -e "${BLUE}=== 服務狀態檢查 ===${NC}"
    echo ""

    services=(
        "ArangoDB:$ARANGODB_PORT"
        "ChromaDB:$CHROMADB_PORT"
        "FastAPI:$FASTAPI_PORT"
        "MCP Server:$MCP_SERVER_PORT"
    )

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

# 函數：停止所有服務
stop_all() {
    echo -e "${BLUE}=== 停止所有服務 ===${NC}"

    ports=($ARANGODB_PORT $CHROMADB_PORT $FASTAPI_PORT $MCP_SERVER_PORT)
    service_names=("ArangoDB" "ChromaDB" "FastAPI" "MCP Server")

    for i in "${!ports[@]}"; do
        port=${ports[$i]}
        name=${service_names[$i]}
        if check_port $port; then
            echo -e "${YELLOW}停止 $name (端口 $port)...${NC}"
            kill_port $port "$name"
        fi
    done

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
                echo -e "${BLUE}啟動所有服務...${NC}"
                start_arangodb || true
                start_chromadb || true
                start_fastapi || true
                echo -e "${GREEN}=== 啟動完成 ===${NC}"
                check_status
                ;;
            arangodb)
                start_arangodb
                ;;
            chromadb)
                start_chromadb
                ;;
            fastapi)
                start_fastapi
                ;;
            mcp)
                start_mcp_server
                ;;
            status)
                check_status
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
