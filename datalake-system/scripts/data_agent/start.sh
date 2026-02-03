#!/bin/bash
# 代碼功能說明: Data Agent 服務啟動腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

set -e

# 獲取腳本目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATALAKE_SYSTEM_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 日誌目錄
LOG_DIR="$DATALAKE_SYSTEM_DIR/logs"
PID_FILE="$LOG_DIR/data_agent.pid"
LOG_FILE="$LOG_DIR/data_agent.log"
ERROR_LOG_FILE="$LOG_DIR/data_agent_error.log"

# 創建日誌目錄
mkdir -p "$LOG_DIR"

# 檢查服務是否已經運行
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  Data Agent 服務已在運行中 (PID: $PID)"
        echo "   使用 ./stop.sh 停止服務，或使用 ./restart.sh 重啟服務"
        exit 1
    else
        echo "🧹 清理舊的 PID 文件"
        rm -f "$PID_FILE"
    fi
fi

# 進入 datalake-system 目錄
cd "$DATALAKE_SYSTEM_DIR"

# 激活 datalake-system/venv（獨立示範系統統一虛擬環境）
if [ -f "$DATALAKE_SYSTEM_DIR/venv/bin/activate" ]; then
    source "$DATALAKE_SYSTEM_DIR/venv/bin/activate"
fi

# 檢查 Python 環境
if ! command -v python3 &> /dev/null; then
    echo "❌ 錯誤: 未找到 python3"
    exit 1
fi

# 檢查環境配置
echo "📋 檢查環境配置..."
python3 "$DATALAKE_SYSTEM_DIR/scripts/check_environment.py" || {
    echo "❌ 環境配置檢查失敗，請修復後重試"
    exit 1
}

# 檢查依賴
if ! python3 -c "import fastapi, uvicorn" 2>/dev/null; then
    echo "❌ 錯誤: 缺少必要的 Python 依賴 (fastapi, uvicorn)"
    echo "   請運行: cd $DATALAKE_SYSTEM_DIR && pip install -r requirements.txt"
    exit 1
fi

# 檢查 boto3 依賴（用於 SeaweedFS S3 API）
if ! python3 -c "import boto3" 2>/dev/null; then
    echo "❌ 錯誤: 缺少必要的 Python 依賴 (boto3)"
    echo "   請運行: cd $DATALAKE_SYSTEM_DIR && pip install -r requirements.txt"
    exit 1
fi

# 檢查 pandas 依賴（用於 Datalake 查詢結果處理）
if ! python3 -c "import pandas" 2>/dev/null; then
    echo "❌ 錯誤: 缺少必要的 Python 依賴 (pandas)"
    echo "   請運行: cd $DATALAKE_SYSTEM_DIR && pip install -r requirements.txt"
    exit 1
fi

# 啟動服務
echo "🚀 啟動 Data Agent 服務 (Datalake System)..."
echo "   Datalake System 目錄: $DATALAKE_SYSTEM_DIR"
echo "   虛擬環境: $DATALAKE_SYSTEM_DIR/venv (若存在)"
echo "   日誌文件: $LOG_FILE"
echo "   錯誤日誌: $ERROR_LOG_FILE"
echo "   PID 文件: $PID_FILE"
echo ""

# 啟動服務並記錄 PID
nohup python3 "$DATALAKE_SYSTEM_DIR/scripts/start_data_agent_service.py" >> "$LOG_FILE" 2>> "$ERROR_LOG_FILE" &
PID=$!

# 保存 PID
echo $PID > "$PID_FILE"

# 等待服務啟動
sleep 3

# 檢查服務是否成功啟動
if ps -p "$PID" > /dev/null 2>&1; then
    echo "✅ Data Agent 服務已啟動"
    echo "   PID: $PID"
    echo "   日誌: tail -f $LOG_FILE"
    echo "   錯誤日誌: tail -f $ERROR_LOG_FILE"
    echo "   健康檢查: curl http://localhost:8004/health"
    echo ""
    echo "📋 查看日誌: ./scripts/data_agent/view_logs.sh"
    echo "🛑 停止服務: ./scripts/data_agent/stop.sh"
    echo "📊 查看狀態: ./scripts/data_agent/status.sh"
else
    echo "❌ 服務啟動失敗，請檢查日誌:"
    echo "   標準日誌: $LOG_FILE"
    echo "   錯誤日誌: $ERROR_LOG_FILE"
    rm -f "$PID_FILE"
    exit 1
fi
