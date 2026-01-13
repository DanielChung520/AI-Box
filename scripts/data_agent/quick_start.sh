#!/bin/bash
# 代碼功能說明: Data Agent 快速啟動和觀察腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Data Agent 快速啟動和觀察"
echo "=============================="
echo ""

# 檢查服務狀態
echo "📊 檢查服務狀態..."
"$SCRIPT_DIR/status.sh"
echo ""

# 如果服務未運行，則啟動
if [ ! -f "$SCRIPT_DIR/../logs/data_agent/data_agent.pid" ] || ! ps -p $(cat "$SCRIPT_DIR/../logs/data_agent/data_agent.pid" 2>/dev/null) > /dev/null 2>&1; then
    echo "🔄 服務未運行，正在啟動..."
    "$SCRIPT_DIR/start.sh"
    echo ""
    sleep 2
fi

# 顯示服務狀態
echo "📊 當前服務狀態:"
"$SCRIPT_DIR/status.sh"
echo ""

# 顯示最後 20 行日誌
echo "📋 最後 20 行日誌:"
"$SCRIPT_DIR/view_logs.sh" last 20
echo ""

echo "💡 提示:"
echo "   - 實時查看日誌: ./scripts/data_agent/view_logs.sh"
echo "   - 查看錯誤日誌: ./scripts/data_agent/view_logs.sh error"
echo "   - 查看服務狀態: ./scripts/data_agent/status.sh"
echo "   - 停止服務: ./scripts/data_agent/stop.sh"
