#!/bin/bash
# 代碼功能說明: 啟動 RQ Worker 腳本
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 項目根目錄
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 日誌目錄
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 加載 .env 文件（如果存在）
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 確定 Python 路徑
PYTHON_CMD="python3"

# 檢查虛擬環境
if [ -d "venv" ]; then
    source venv/bin/activate
    PYTHON_CMD="venv/bin/python"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON_CMD=".venv/bin/python"
fi

# 檢查 RQ 是否安裝
if ! "$PYTHON_CMD" -c "import rq" 2>/dev/null; then
    echo -e "${RED}錯誤: RQ 未安裝${NC}"
    echo -e "${YELLOW}請安裝: pip install rq${NC}"
    exit 1
fi

# 檢查 Redis 連接
if ! "$PYTHON_CMD" -c "from database.redis import get_redis_client; get_redis_client().ping()" 2>/dev/null; then
    echo -e "${RED}錯誤: 無法連接到 Redis${NC}"
    echo -e "${YELLOW}請確保 Redis 服務正在運行${NC}"
    exit 1
fi

# 隊列名稱（可通過參數指定）
QUEUE_NAME=${1:-"file_processing"}

# Worker 名稱
WORKER_NAME="rq_worker_${QUEUE_NAME}_$$"

echo -e "${GREEN}=== 啟動 RQ Worker ===${NC}"
echo -e "${GREEN}隊列名稱: ${QUEUE_NAME}${NC}"
echo -e "${GREEN}Worker 名稱: ${WORKER_NAME}${NC}"
echo -e "${GREEN}日誌文件: ${LOG_DIR}/rq_worker_${QUEUE_NAME}.log${NC}"
echo ""

# 設置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 啟動 RQ Worker
"$PYTHON_CMD" -m rq worker \
    "$QUEUE_NAME" \
    --name "$WORKER_NAME" \
    --url "${REDIS_URL:-redis://localhost:6379/0}" \
    --with-scheduler \
    > "$LOG_DIR/rq_worker_${QUEUE_NAME}.log" 2>&1 &

WORKER_PID=$!

echo -e "${GREEN}✅ RQ Worker 已啟動${NC}"
echo -e "${GREEN}   PID: ${WORKER_PID}${NC}"
echo -e "${GREEN}   隊列: ${QUEUE_NAME}${NC}"
echo -e "${GREEN}   日誌: ${LOG_DIR}/rq_worker_${QUEUE_NAME}.log${NC}"
echo ""
echo -e "${YELLOW}提示: 使用以下命令查看日誌${NC}"
echo -e "${YELLOW}   tail -f ${LOG_DIR}/rq_worker_${QUEUE_NAME}.log${NC}"
