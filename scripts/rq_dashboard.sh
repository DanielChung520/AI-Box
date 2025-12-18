#!/bin/bash
# 代碼功能說明: RQ Dashboard 啟動腳本
# 創建日期: 2025-12-12
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-12

# 激活虛擬環境並啟動 RQ Dashboard
cd "$(dirname "$0")/.." || exit 1
source venv/bin/activate

# 從環境變數讀取配置，或使用默認值
REDIS_URL="${REDIS_URL:-redis://localhost:6379/0}"
PORT="${RQ_DASHBOARD_PORT:-9181}"

# 修改時間：2025-12-12 - 正確解析命令行參數中的 --port
prev_arg=""
for arg in "$@"; do
    if [[ $prev_arg == --port ]]; then
        PORT="$arg"
        prev_arg=""
    elif [[ $arg == --port=* ]]; then
        PORT="${arg#--port=}"
        prev_arg=""
    elif [[ $arg == --port ]]; then
        prev_arg="$arg"
    else
        prev_arg=""
    fi
done

echo "啟動 RQ Dashboard..."
echo "Redis URL: $REDIS_URL"
echo "端口: $PORT"
echo "訪問地址: http://localhost:$PORT"
echo ""

# 構建命令參數，確保 --port 參數正確
rq-dashboard --redis-url "$REDIS_URL" --port "$PORT"
