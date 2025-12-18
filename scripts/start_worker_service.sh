#!/bin/bash
# 代碼功能說明: 啟動 RQ Worker Service（帶監控功能）
# 創建日期: 2025-12-12
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-12

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
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

# 設置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 解析參數
MONITOR=false
QUEUES=("kg_extraction" "vectorization" "file_processing")
WORKER_NAME=""
CHECK_INTERVAL=30

while [[ $# -gt 0 ]]; do
    case $1 in
        --monitor)
            MONITOR=true
            shift
            ;;
        --queues)
            shift
            QUEUES=("$@")
            break
            ;;
        --name)
            WORKER_NAME="$2"
            shift 2
            ;;
        --check-interval)
            CHECK_INTERVAL="$2"
            shift 2
            ;;
        *)
            echo -e "${RED}未知參數: $1${NC}"
            exit 1
            ;;
    esac
done

# 構建命令
CMD=("$PYTHON_CMD" -m workers.service)
CMD+=(--queues "${QUEUES[@]}")

if [ -n "$WORKER_NAME" ]; then
    CMD+=(--name "$WORKER_NAME")
fi

if [ "$MONITOR" = true ]; then
    CMD+=(--monitor --check-interval "$CHECK_INTERVAL")
fi

echo -e "${BLUE}=== 啟動 RQ Worker Service ===${NC}"
echo -e "${GREEN}隊列: ${QUEUES[*]}${NC}"
echo -e "${GREEN}監控模式: ${MONITOR}${NC}"
if [ -n "$WORKER_NAME" ]; then
    echo -e "${GREEN}Worker 名稱: ${WORKER_NAME}${NC}"
fi
echo ""

# 啟動服務
"${CMD[@]}"
