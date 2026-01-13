#!/bin/bash
# 代碼功能說明: 庫管員Agent服務啟動腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
AI_BOX_ROOT="$(cd "$DATALAKE_SYSTEM_DIR/.." && pwd)"

LOG_DIR="$DATALAKE_SYSTEM_DIR/logs"
PID_FILE="$LOG_DIR/warehouse_manager_agent.pid"
LOG_FILE="$LOG_DIR/warehouse_manager_agent.log"
ERROR_LOG_FILE="$LOG_DIR/warehouse_manager_agent_error.log"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  庫管員Agent服務已在運行中 (PID: $PID)"
        exit 1
    else
        rm -f "$PID_FILE"
    fi
fi

cd "$DATALAKE_SYSTEM_DIR"

if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 未找到 python3"
    exit 1
fi

echo "🚀 啟動庫管員Agent服務..."
nohup python3 "$DATALAKE_SYSTEM_DIR/scripts/start_warehouse_manager_agent_service.py" >> "$LOG_FILE" 2>> "$ERROR_LOG_FILE" &
PID=$!
echo $PID > "$PID_FILE"
sleep 3

if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ 庫管員Agent服務已啟動 (PID: $PID)"
else
    echo "❌ 服務啟動失敗"
    rm -f "$PID_FILE"
    exit 1
fi
