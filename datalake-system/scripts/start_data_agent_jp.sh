#!/bin/bash
# Data-Agent-JP 服務啟動腳本
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AI_BOX_ROOT="$(dirname "$SCRIPT_DIR")/.."
VENV_PATH="/home/daniel/ai-box/venv"
SERVICE_PORT="${DATA_AGENT_SERVICE_PORT:-8004}"
LOG_FILE="/tmp/data_agent_jp.log"
PID_FILE="/tmp/data_agent_jp.pid"

# 環境變數
export LD_LIBRARY_PATH="/home/daniel/instantclient_23_26:/home/daniel/oracle_libs:$LD_LIBRARY_PATH"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_venv() {
    if [ ! -d "$VENV_PATH" ]; then
        log_error "Virtual environment not found: $VENV_PATH"
        exit 1
    fi
    log_info "Virtual environment found: $VENV_PATH"
}

check_port() {
    if lsof -i:$SERVICE_PORT > /dev/null 2>&1; then
        log_warn "Port $SERVICE_PORT is already in use"
        read -p "Do you want to kill the existing process? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            fuser -k ${SERVICE_PORT}/tcp 2>/dev/null || true
            log_info "Killed process on port $SERVICE_PORT"
            sleep 2
        else
            log_info "Using existing process"
            exit 0
        fi
    fi
}

stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            log_info "Stopping existing service (PID: $PID)..."
            kill "$PID" 2>/dev/null || true
            sleep 2
            kill -9 "$PID" 2>/dev/null || true
        fi
        rm -f "$PID_FILE"
    fi

    # 清理殘留進程
    pkill -f "start_data_agent_jp_service.py" 2>/dev/null || true
    sleep 1
}

start_service() {
    log_info "Starting Data-Agent-JP Service..."

    cd "$SCRIPT_DIR"

    # 啟動服務
    nohup "$VENV_PATH/bin/python3" "start_data_agent_jp_service.py" \
        >> "$LOG_FILE" 2>&1 &

    PID=$!
    echo "$PID" > "$PID_FILE"

    log_info "Service started with PID: $PID"
    log_info "Log file: $LOG_FILE"

    # 等待服務啟動
    local retries=10
    local count=0
    while [ $count -lt $retries ]; do
        if curl -s "http://127.0.0.1:${SERVICE_PORT}/jp/health" > /dev/null 2>&1; then
            log_info "Service is ready!"
            echo ""
            echo "=========================================="
            echo "  Data-Agent-JP Service Started Successfully"
            echo "=========================================="
            echo "  Port:     $SERVICE_PORT"
            echo "  PID:      $PID"
            echo "  Health:   http://localhost:${SERVICE_PORT}/jp/health"
            echo "  Execute:  http://localhost:${SERVICE_PORT}/jp/execute"
            echo "=========================================="
            echo ""
            echo "Logs: tail -f $LOG_FILE"
            return 0
        fi
        sleep 1
        count=$((count + 1))
    done

    log_error "Service failed to start within ${retries} seconds"
    log_error "Check logs: tail -f $LOG_FILE"
    return 1
}

status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo -e "${GREEN}[RUNNING]${NC} Data-Agent-JP (PID: $PID)"
            curl -s "http://127.0.0.1:${SERVICE_PORT}/jp/health" | python3 -m json.tool 2>/dev/null || echo "Health check failed"
            return 0
        fi
    fi
    echo -e "${YELLOW}[STOPPED]${NC} Data-Agent-JP"
    return 1
}

usage() {
    echo "Usage: $0 {start|stop|restart|status}"
    echo ""
    echo "Commands:"
    echo "  start    Start the service"
    echo "  stop     Stop the service"
    echo "  restart  Restart the service"
    echo "  status   Check service status"
    echo ""
    echo "Environment Variables:"
    echo "  DATA_AGENT_SERVICE_PORT  Service port (default: 8004)"
}

case "${1:-start}" in
    start)
        check_venv
        check_port
        start_service
        ;;
    stop)
        stop_service
        log_info "Service stopped"
        ;;
    restart)
        stop_service
        check_venv
        start_service
        ;;
    status)
        status
        ;;
    *)
        usage
        exit 1
        ;;
esac
