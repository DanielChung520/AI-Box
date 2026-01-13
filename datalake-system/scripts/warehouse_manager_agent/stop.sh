#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$DATALAKE_SYSTEM_DIR/logs"
PID_FILE="$LOG_DIR/warehouse_manager_agent.pid"
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  服務未運行"
    exit 0
fi
PID=$(cat "$PID_FILE")
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  服務未運行"
    rm -f "$PID_FILE"
    exit 0
fi
echo "🛑 停止庫管員Agent服務 (PID: $PID)..."
kill "$PID"
sleep 2
if ps -p "$PID" > /dev/null 2>&1; then
    kill -9 "$PID"
fi
rm -f "$PID_FILE"
echo "✅ 服務已停止"
