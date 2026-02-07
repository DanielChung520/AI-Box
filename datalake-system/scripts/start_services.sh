# 代碼功能說明: Datalake System 服務啟動腳本
# 創建日期: 2026-01-29
# 作者: Daniel Chung
# 最後修改日期: 2026-02-01

# Datalake System 服務管理 - 簡化版 (無 Streamlit)

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$DATALAKE_ROOT"

# 日誌目錄
LOG_DIR="$DATALAKE_ROOT/logs"
mkdir -p "$LOG_DIR"

# 端口配置
DATA_AGENT_PORT="${DATA_AGENT_SERVICE_PORT:-8004}"
MM_AGENT_PORT="${MM_AGENT_SERVICE_PORT:-8003}"
API_SERVER_PORT="${API_SERVER_PORT:-8005}"
FRONTEND_PORT="${FRONTEND_PORT:-8503}"
SEAWEEDFS_S3_PORT="${DATALAKE_SEAWEEDFS_S3_PORT:-8334}"
SEAWEEDFS_FILER_PORT="${DATALAKE_SEAWEEDFS_FILER_PORT:-8889}"

# 清除端口進程
clear_port() {
    local port=$1
    echo -e "${YELLOW}🧹 清除端口 $port...${NC}"
    fuser -k ${port}/tcp 2>/dev/null || true
    sleep 1
}

# 啟動 Data-Agent
start_data_agent() {
    clear_port $DATA_AGENT_PORT
    echo -e "${GREEN}🚀 啟動 Data-Agent (端口 $DATA_AGENT_PORT)...${NC}"
    "$SCRIPT_DIR/data_agent/start.sh" || {
        echo -e "${RED}❌ Data-Agent 啟動失敗${NC}"
        return 1
    }
    sleep 2
    if check_port $DATA_AGENT_PORT; then
        echo -e "${GREEN}   ✅ Data-Agent 已啟動: http://localhost:$DATA_AGENT_PORT${NC}"
    else
        echo -e "${RED}   ❌ Data-Agent 啟動失敗${NC}"
    fi
}

# 啟動 MM-Agent
start_mm_agent() {
    clear_port $MM_AGENT_PORT
    local MM_AGENT_DIR="$DATALAKE_ROOT/mm_agent"
    if [ ! -f "$MM_AGENT_DIR/main.py" ]; then
        echo -e "${RED}❌ MM-Agent 主程序不存在${NC}"
        return 1
    fi
    echo -e "${GREEN}🚀 啟動 MM-Agent (端口 $MM_AGENT_PORT)...${NC}"
    cd "$DATALAKE_ROOT"
    /home/daniel/ai-box/venv/bin/python -c "
import sys
from pathlib import Path
datalake_system_dir = Path('$MM_AGENT_DIR').resolve().parent
ai_box_root = Path('$MM_AGENT_DIR').resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))
import uvicorn
from mm_agent.main import app
uvicorn.run(app, host='0.0.0.0', port=int('$MM_AGENT_PORT'))
" >> "$LOG_DIR/mm_agent.log" 2>> "$LOG_DIR/mm_agent_error.log" &
    echo $! > "$LOG_DIR/mm_agent.pid"
    sleep 3
    if check_port $MM_AGENT_PORT; then
        echo -e "${GREEN}   ✅ MM-Agent 已啟動: http://localhost:$MM_AGENT_PORT${NC}"
    else
        echo -e "${RED}   ❌ MM-Agent 啟動失敗${NC}"
        rm -f "$LOG_DIR/mm_agent.pid"
        return 1
    fi
}

# 啟動 API Server (Frontend API)
start_api_server() {
    clear_port $API_SERVER_PORT
    local FRONTEND_DIR="$DATALAKE_ROOT/frontend"
    if [ ! -f "$FRONTEND_DIR/api_server.py" ]; then
        echo -e "${RED}❌ API Server 不存在${NC}"
        return 1
    fi
    echo -e "${GREEN}🚀 啟動 API Server (端口 $API_SERVER_PORT)...${NC}"
    nohup /home/daniel/ai-box/venv/bin/python "$FRONTEND_DIR/api_server.py" >> "$LOG_DIR/api_server.log" 2>> "$LOG_DIR/api_server_error.log" &
    echo $! > "$LOG_DIR/api_server.pid"
    sleep 3
    if check_port $API_SERVER_PORT; then
        echo -e "${GREEN}   ✅ API Server 已啟動: http://localhost:$API_SERVER_PORT${NC}"
    else
        echo -e "${RED}   ❌ API Server 啟動失敗${NC}"
        rm -f "$LOG_DIR/api_server.pid"
        return 1
    fi
}

# 啟動 Frontend (React)
start_frontend() {
    clear_port $FRONTEND_PORT
    local FRONTEND_DIR="$DATALAKE_ROOT/frontend"
    if [ ! -d "$FRONTEND_DIR" ]; then
        echo -e "${RED}❌ Frontend 目錄不存在${NC}"
        return 1
    fi
    echo -e "${GREEN}🚀 啟動 Frontend (端口 $FRONTEND_PORT)...${NC}"
    cd "$FRONTEND_DIR"
    nohup npm run dev >> "$LOG_DIR/frontend.log" 2>> "$LOG_DIR/frontend_error.log" &
    echo $! > "$LOG_DIR/frontend.pid"
    sleep 5
    if check_port $FRONTEND_PORT; then
        echo -e "${GREEN}   ✅ Frontend 已啟動: http://localhost:$FRONTEND_PORT${NC}"
    else
        echo -e "${RED}   ❌ Frontend 啟動失敗${NC}"
        rm -f "$LOG_DIR/frontend.pid"
        return 1
    fi
}

# 停止 Data-Agent
stop_data_agent() {
    clear_port $DATA_AGENT_PORT
    rm -f "$LOG_DIR/data_agent.pid" 2>/dev/null || true
}

# 停止 API Server
stop_api_server() {
    clear_port $API_SERVER_PORT
    rm -f "$LOG_DIR/api_server.pid" 2>/dev/null || true
}

# 停止 Frontend
stop_frontend() {
    clear_port $FRONTEND_PORT
    rm -f "$LOG_DIR/frontend.pid" 2>/dev/null || true
}

# 停止 MM-Agent
stop_mm_agent() {
    clear_port $MM_AGENT_PORT
    rm -f "$LOG_DIR/mm_agent.pid" 2>/dev/null || true
}

# 檢查端口
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    fi
    if lsof -ti :$port >/dev/null 2>&1; then
        return 0
    fi
    return 1
}

# 狀態檢查
check_status() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Datalake System 服務狀態${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""

    echo -e "${GREEN}📦 Datalake (SeaweedFS S3: $SEAWEEDFS_S3_PORT)${NC}"
    if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$SEAWEEDFS_FILER_PORT/" 2>/dev/null | grep -q "200\|301\|302"; then
        echo -e "   ${GREEN}✅ 運行中${NC} - http://localhost:$SEAWEEDFS_S3_PORT (S3)"
    elif check_port $SEAWEEDFS_S3_PORT; then
        echo -e "   ${GREEN}✅ 端口監聽中${NC}"
    else
        echo -e "   ${RED}❌ 未運行${NC}"
    fi
    echo ""

    echo -e "${GREEN}🤖 Data-Agent (端口 $DATA_AGENT_PORT)${NC}"
    if check_port $DATA_AGENT_PORT; then
        echo -e "   ${GREEN}✅ 運行中${NC} - http://localhost:$DATA_AGENT_PORT"
    else
        echo -e "   ${RED}❌ 未運行${NC}"
    fi
    echo ""

    echo -e "${GREEN}📦 MM-Agent (端口 $MM_AGENT_PORT)${NC}"
    if check_port $MM_AGENT_PORT; then
        echo -e "   ${GREEN}✅ 運行中${NC} - http://localhost:$MM_AGENT_PORT"
        # 檢查健康狀態
        local health_status=$(curl -s http://localhost:$MM_AGENT_PORT/health 2>/dev/null | grep -o '"status":"healthy"' || echo "")
        if [ -n "$health_status" ]; then
            echo -e "   ${GREEN}   Health: healthy${NC}"
        fi
    else
        echo -e "   ${RED}❌ 未運行${NC}"
    fi
    echo ""

    echo -e "${GREEN}🔌 API Server (端口 $API_SERVER_PORT)${NC}"
    if check_port $API_SERVER_PORT; then
        echo -e "   ${GREEN}✅ 運行中${NC} - http://localhost:$API_SERVER_PORT"
    else
        echo -e "   ${RED}❌ 未運行${NC}"
    fi
    echo ""

    echo -e "${GREEN}🎨 Frontend - React (端口 $FRONTEND_PORT)${NC}"
    if check_port $FRONTEND_PORT; then
        echo -e "   ${GREEN}✅ 運行中${NC} - http://localhost:$FRONTEND_PORT"
    else
        echo -e "   ${RED}❌ 未運行${NC}"
    fi
    echo ""
}

show_usage() {
    echo "Datalake System 服務管理"
    echo ""
    echo "用法: $0 <命令> [服務]"
    echo ""
    echo "命令:"
    echo "  start     啟動服務（不指定服務則啟動全部）"
    echo "  stop      停止服務（不指定服務則停止全部）"
    echo "  status    檢查所有服務狀態"
    echo "  restart   重啟服務"
    echo ""
    echo "服務:"
    echo "  all           全部（預設）"
    echo "  data_agent    Data-Agent (端口 $DATA_AGENT_PORT)"
    echo "  mm_agent      MM-Agent (端口 $MM_AGENT_PORT)"
    echo "  api_server    API Server (端口 $API_SERVER_PORT)"
    echo "  frontend      Frontend - React (端口 $FRONTEND_PORT)"
    echo ""
    echo "範例:"
    echo "  $0 start              # 啟動全部"
    echo "  $0 start mm_agent     # 僅啟動 MM-Agent"
    echo "  $0 start api_server   # 僅啟動 API Server"
    echo "  $0 start frontend     # 僅啟動 React Frontend"
    echo "  $0 status             # 檢查狀態"
    echo "  $0 stop               # 停止全部"
}

CMD="${1:-status}"
SVC="${2:-all}"

case "$CMD" in
    start)
        case "$SVC" in
            all)
                start_data_agent
                start_mm_agent
                start_api_server
                start_frontend
                echo ""
                check_status
                ;;
            data_agent)
                start_data_agent
                ;;
            mm_agent)
                start_mm_agent
                ;;
            api_server)
                start_api_server
                ;;
            frontend)
                start_frontend
                ;;
            *)
                echo -e "${RED}未知服務: $SVC${NC}"
                show_usage
                exit 1
                ;;
        esac
        ;;
    stop)
        case "$SVC" in
            all)
                echo "🛑 停止所有服務..."
                stop_data_agent
                stop_mm_agent
                stop_api_server
                stop_frontend
                echo -e "${GREEN}✅ 已停止${NC}"
                ;;
            data_agent)
                stop_data_agent
                ;;
            mm_agent)
                stop_mm_agent
                ;;
            api_server)
                stop_api_server
                ;;
            frontend)
                stop_frontend
                ;;
            *)
                echo -e "${RED}未知服務: $SVC${NC}"
                show_usage
                exit 1
                ;;
        esac
        ;;
    restart)
        case "$SVC" in
            all)
                $0 stop all
                sleep 2
                $0 start all
                ;;
            data_agent)
                stop_data_agent
                sleep 2
                start_data_agent
                ;;
            mm_agent)
                stop_mm_agent
                sleep 2
                start_mm_agent
                ;;
            api_server)
                stop_api_server
                sleep 2
                start_api_server
                ;;
            frontend)
                stop_frontend
                sleep 2
                start_frontend
                ;;
            *)
                echo -e "${RED}未知服務: $SVC${NC}"
                show_usage
                exit 1
                ;;
        esac
        ;;
    status)
        check_status
        ;;
    *)
        show_usage
        exit 1
        ;;
esac
