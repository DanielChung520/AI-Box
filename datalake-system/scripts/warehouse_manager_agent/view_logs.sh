#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$DATALAKE_SYSTEM_DIR/logs"
LOG_FILE="$LOG_DIR/warehouse_manager_agent.log"
ERROR_LOG_FILE="$LOG_DIR/warehouse_manager_agent_error.log"
LOG_TYPE="${1:-all}"
case "$LOG_TYPE" in
    error|err)
        if [ -f "$ERROR_LOG_FILE" ]; then
            tail -f "$ERROR_LOG_FILE"
        else
            echo "⚠️  錯誤日誌文件不存在"
        fi
        ;;
    *)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "⚠️  日誌文件不存在"
        fi
        ;;
esac
