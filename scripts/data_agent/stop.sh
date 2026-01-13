#!/bin/bash
# 代碼功能說明: Data Agent 服務停止腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# PID 文件
PID_FILE="$PROJECT_ROOT/logs/data_agent/data_agent.pid"

# 檢查 PID 文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  PID 文件不存在，服務可能未運行"
    exit 0
fi

# 讀取 PID
PID=$(cat "$PID_FILE")

# 檢查進程是否存在
if ! ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  進程不存在 (PID: $PID)，清理 PID 文件"
    rm -f "$PID_FILE"
    exit 0
fi

# 停止服務
echo "🛑 停止 Data Agent 服務 (PID: $PID)..."
kill "$PID" || true

# 等待進程結束
for i in {1..10}; do
    if ! ps -p "$PID" > /dev/null 2>&1; then
        break
    fi
    sleep 1
done

# 如果進程仍在運行，強制終止
if ps -p "$PID" > /dev/null 2>&1; then
    echo "⚠️  進程未正常終止，強制終止..."
    kill -9 "$PID" || true
    sleep 1
fi

# 清理 PID 文件
rm -f "$PID_FILE"

echo "✅ Data Agent 服務已停止"
