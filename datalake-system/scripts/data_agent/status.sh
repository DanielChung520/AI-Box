#!/bin/bash
# 代碼功能說明: Data Agent 服務狀態檢查腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

PID_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent.pid"
LOG_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent.log"
PORT="${DATA_AGENT_SERVICE_PORT:-8004}"

echo "🤖 Data-Agent 服務狀態 (Datalake System)"
echo "======================================"
echo ""

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

find_data_agent_pid() {
    local port=$1
    lsof -ti :$port 2>/dev/null | head -1
}

actual_pid=$(find_data_agent_pid $PORT)
file_pid=""
[ -f "$PID_FILE" ] && file_pid=$(cat "$PID_FILE")

echo "端口: $PORT"
echo "PID 文件: ${file_pid:-不存在}"
echo "實際監聽 PID: ${actual_pid:-未監聽}"

if [ -n "$actual_pid" ]; then
    echo ""
    echo "狀態: ✅ 運行中 (PID: $actual_pid)"

    if [ "$actual_pid" != "$file_pid" ] && [ -n "$file_pid" ]; then
        echo "⚠️  PID 不一致：文件=$file_pid，實際=$actual_pid"
        echo "   建議更新 PID 文件或重新啟動服務"
    fi

    echo ""
    echo "進程信息:"
    ps -p $actual_pid -o pid,ppid,user,%cpu,%mem,etime,command 2>/dev/null || true

    echo ""
    echo "API 健康檢查:"

    if curl -s -f "http://localhost:$PORT/execute" \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"task_id":"health_check","task_type":"ping","task_data":{}}' \
        > /dev/null 2>&1; then
        echo "  ✅ API 響應正常"
    else
        response=$(curl -s -w "\n%{http_code}" "http://localhost:$PORT/execute" \
            -X POST \
            -H "Content-Type: application/json" \
            -d '{"task_id":"health_check","task_type":"ping","task_data":{}}' 2>/dev/null || echo "")
        http_code=$(echo "$response" | tail -1)
        if [ "$http_code" = "422" ] || [ "$http_code" = "400" ]; then
            echo "  ⚠️  API 響應異常 (HTTP $http_code - 可能是 Schema 錯誤)"
        else
            echo "  ⚠️  API 無響應 (HTTP ${http_code:-timeout})"
        fi
    fi

    echo ""
    echo "日誌文件:"
    if [ -f "$LOG_FILE" ]; then
        echo "  路徑: $LOG_FILE"
        echo "  大小: $(du -h "$LOG_FILE" | cut -f1)"
        echo "  行數: $(wc -l < "$LOG_FILE")"
        echo "  最後 3 行:"
        tail -3 "$LOG_FILE" 2>/dev/null | sed 's/^/    /'
    else
        echo "  ⚠️  日誌文件不存在"
    fi

elif [ -n "$file_pid" ]; then
    echo ""
    echo "狀態: ❌ 未運行"
    echo "原因: PID 文件存在但端口未監聽"
    echo "文件中的 PID: $file_pid"
    echo ""
    echo "💡 建議操作:"
    echo "   1. 清理 PID 文件: rm -f $PID_FILE"
    echo "   2. 重新啟動服務: ./scripts/data_agent/start.sh"
else
    echo ""
    echo "狀態: ❌ 未運行"
    echo ""
    echo "💡 建議操作:"
    echo "   1. 啟動服務: ./scripts/data_agent/start.sh"
    echo "   2. 或使用: ./scripts/start_services.sh start data_agent"
fi
