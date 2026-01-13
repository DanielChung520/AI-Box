#!/bin/bash
# 代碼功能說明: Data Agent 服務狀態檢查腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# PID 文件
PID_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent.pid"
LOG_FILE="$DATALAKE_SYSTEM_DIR/logs/data_agent.log"

echo "📊 Data Agent 服務狀態 (Datalake System)"
echo "===================="
echo ""

# 檢查 PID 文件
if [ ! -f "$PID_FILE" ]; then
    echo "狀態: ❌ 未運行"
    echo "PID 文件: 不存在"
    exit 0
fi

# 讀取 PID
PID=$(cat "$PID_FILE")

# 檢查進程
if ps -p "$PID" > /dev/null 2>&1; then
    echo "狀態: ✅ 運行中"
    echo "PID: $PID"

    # 獲取進程信息
    if command -v ps &> /dev/null; then
        echo ""
        echo "進程信息:"
        ps -p "$PID" -o pid,ppid,user,start,time,command 2>/dev/null || true
    fi

    # 檢查端口
    PORT="${DATA_AGENT_SERVICE_PORT:-8004}"
    if command -v lsof &> /dev/null; then
        if lsof -i :$PORT > /dev/null 2>&1; then
            echo ""
            echo "端口 $PORT: ✅ 監聽中"
        else
            echo ""
            echo "端口 $PORT: ⚠️  未監聽"
        fi
    fi

    # 健康檢查
    echo ""
    echo "健康檢查:"
    if command -v curl &> /dev/null; then
        HEALTH_URL="http://localhost:${PORT:-8004}/health"
        if curl -s -f "$HEALTH_URL" > /dev/null 2>&1; then
            echo "  ✅ 服務正常"
            curl -s "$HEALTH_URL" | python3 -m json.tool 2>/dev/null || curl -s "$HEALTH_URL"
        else
            echo "  ⚠️  服務無響應"
        fi
    else
        echo "  ⚠️  未安裝 curl，無法進行健康檢查"
    fi
else
    echo "狀態: ❌ 未運行（PID 文件存在但進程不存在）"
    echo "PID: $PID (進程不存在)"
    echo ""
    echo "💡 建議: 清理 PID 文件並重新啟動服務"
fi

# 日誌文件信息
echo ""
echo "日誌文件:"
if [ -f "$LOG_FILE" ]; then
    echo "  路徑: $LOG_FILE"
    echo "  大小: $(du -h "$LOG_FILE" | cut -f1)"
    echo "  行數: $(wc -l < "$LOG_FILE")"
    echo "  最後更新: $(stat -f "%Sm" "$LOG_FILE" 2>/dev/null || stat -c "%y" "$LOG_FILE" 2>/dev/null || echo "未知")"
else
    echo "  ⚠️  日誌文件不存在"
fi
