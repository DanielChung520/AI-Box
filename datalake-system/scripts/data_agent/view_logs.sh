#!/bin/bash
# 代碼功能說明: Data Agent 服務日誌查看腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 日誌文件
LOG_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent.log"
ERROR_LOG_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent_error.log"

# 檢查日誌文件是否存在
if [ ! -f "$LOG_FILE" ] && [ ! -f "$ERROR_LOG_FILE" ]; then
    echo "⚠️  日誌文件不存在"
    echo "   標準日誌: $LOG_FILE"
    echo "   錯誤日誌: $ERROR_LOG_FILE"
    echo "   服務可能尚未啟動，請先運行: ./scripts/data_agent/start.sh"
    exit 1
fi

# 解析參數
MODE="${1:-tail}"
LINES="${2:-50}"

case "$MODE" in
    tail|follow|f)
        echo "📋 實時查看日誌 (按 Ctrl+C 退出)"
        echo "   標準日誌: $LOG_FILE"
        echo "   錯誤日誌: $ERROR_LOG_FILE"
        echo ""
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "⚠️  標準日誌文件不存在，查看錯誤日誌..."
            tail -f "$ERROR_LOG_FILE"
        fi
        ;;
    last|l)
        echo "📋 查看最後 $LINES 行日誌"
        echo "   標準日誌: $LOG_FILE"
        echo "   錯誤日誌: $ERROR_LOG_FILE"
        echo ""
        if [ -f "$LOG_FILE" ]; then
            echo "--- 標準日誌 ---"
            tail -n "$LINES" "$LOG_FILE"
        fi
        if [ -f "$ERROR_LOG_FILE" ]; then
            echo ""
            echo "--- 錯誤日誌 ---"
            tail -n "$LINES" "$ERROR_LOG_FILE"
        fi
        ;;
    error|e)
        echo "📋 查看錯誤日誌"
        echo "   錯誤日誌文件: $ERROR_LOG_FILE"
        echo ""
        if [ -f "$ERROR_LOG_FILE" ]; then
            tail -n "$LINES" "$ERROR_LOG_FILE"
        elif [ -f "$LOG_FILE" ]; then
            echo "⚠️  錯誤日誌文件不存在，從標準日誌中過濾錯誤..."
            grep -i "error\|exception\|failed\|traceback" "$LOG_FILE" | tail -n "$LINES"
        else
            echo "❌ 沒有可用的日誌文件"
        fi
        ;;
    search|s)
        if [ -z "$2" ]; then
            echo "❌ 錯誤: 請提供搜索關鍵字"
            echo "   用法: ./view_logs.sh search <關鍵字> [行數]"
            exit 1
        fi
        SEARCH_TERM="$2"
        LINES="${3:-50}"
        echo "📋 搜索日誌: $SEARCH_TERM"
        echo ""
        if [ -f "$LOG_FILE" ]; then
            echo "--- 標準日誌中的結果 ---"
            grep -i "$SEARCH_TERM" "$LOG_FILE" | tail -n "$LINES"
        fi
        if [ -f "$ERROR_LOG_FILE" ]; then
            echo ""
            echo "--- 錯誤日誌中的結果 ---"
            grep -i "$SEARCH_TERM" "$ERROR_LOG_FILE" | tail -n "$LINES"
        fi
        ;;
    stats|stat)
        echo "📋 日誌統計信息"
        echo ""
        if [ -f "$LOG_FILE" ]; then
            echo "標準日誌 ($LOG_FILE):"
            echo "   文件大小: $(du -h "$LOG_FILE" | cut -f1)"
            echo "   總行數: $(wc -l < "$LOG_FILE")"
            echo "   錯誤數量: $(grep -ic "error\|exception\|failed" "$LOG_FILE" || echo "0")"
            echo "   最後更新: $(stat -f "%Sm" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null || echo "未知")"
        fi
        if [ -f "$ERROR_LOG_FILE" ]; then
            echo ""
            echo "錯誤日誌 ($ERROR_LOG_FILE):"
            echo "   文件大小: $(du -h "$ERROR_LOG_FILE" | cut -f1)"
            echo "   總行數: $(wc -l < "$ERROR_LOG_FILE")"
            echo "   最後更新: $(stat -f "%Sm" "$ERROR_LOG_FILE" 2>/dev/null || stat -c "%y" "$ERROR_LOG_FILE" 2>/dev/null || echo "未知")"
        fi
        ;;
    *)
        echo "📋 Data Agent 日誌查看工具"
        echo ""
        echo "用法:"
        echo "  ./view_logs.sh [模式] [參數]"
        echo ""
        echo "模式:"
        echo "  tail, follow, f    - 實時查看日誌（默認）"
        echo "  last, l [行數]     - 查看最後 N 行（默認 50 行）"
        echo "  error, e [行數]    - 查看錯誤日誌（默認 50 行）"
        echo "  search, s <關鍵字> [行數] - 搜索日誌"
        echo "  stats, stat        - 顯示日誌統計信息"
        echo ""
        echo "示例:"
        echo "  ./view_logs.sh                    # 實時查看"
        echo "  ./view_logs.sh last 100            # 查看最後 100 行"
        echo "  ./view_logs.sh error               # 查看錯誤日誌"
        echo "  ./view_logs.sh search 'query' 20   # 搜索 'query' 關鍵字，顯示 20 行"
        echo "  ./view_logs.sh stats               # 顯示統計信息"
        exit 1
        ;;
esac
