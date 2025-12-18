#!/bin/bash
# 代碼功能說明: 清除 RQ 隊列中的任務
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

# 加載 .env 文件（如果存在）
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

# 確定 Python 路徑
PYTHON_CMD="python3"
if [ -d "venv" ]; then
    source venv/bin/activate
    PYTHON_CMD="venv/bin/python"
elif [ -d ".venv" ]; then
    source .venv/bin/activate
    PYTHON_CMD=".venv/bin/python"
fi

# 設置 PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"

# 隊列名稱（默認為 kg_extraction）
QUEUE_NAME=${1:-"kg_extraction"}

echo -e "${BLUE}=== 清除 RQ 隊列任務 ===${NC}"
echo -e "${YELLOW}隊列名稱: ${QUEUE_NAME}${NC}"
echo ""

# 執行清除腳本
"$PYTHON_CMD" << PYEOF
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path('.env'), override=True)

from database.rq.queue import get_task_queue, get_redis_connection
from rq import Queue
from rq.registry import StartedJobRegistry, FinishedJobRegistry, FailedJobRegistry

queue_name = "${QUEUE_NAME}"

print("=== 清除 {} 隊列中的任務 ===\n".format(queue_name))

redis_conn = get_redis_connection()
queue = Queue(queue_name, connection=redis_conn)

# 獲取所有任務 ID
queued_job_ids = queue.get_job_ids(0, -1)
started_registry = StartedJobRegistry(queue_name, connection=redis_conn)
started_job_ids = started_registry.get_job_ids(0, -1)
finished_registry = FinishedJobRegistry(queue_name, connection=redis_conn)
finished_job_ids = finished_registry.get_job_ids(0, -1)
failed_registry = FailedJobRegistry(queue_name, connection=redis_conn)
failed_job_ids = failed_registry.get_job_ids(0, -1)

all_job_ids = set(queued_job_ids + started_job_ids + finished_job_ids + failed_job_ids)

print("找到以下任務:")
print("  等待中 (queued): {}".format(len(queued_job_ids)))
print("  執行中 (started): {}".format(len(started_job_ids)))
print("  已完成 (finished): {}".format(len(finished_job_ids)))
print("  失敗 (failed): {}".format(len(failed_job_ids)))
print("  總計: {}".format(len(all_job_ids)))
print()

if len(all_job_ids) == 0:
    print("✅ 隊列中沒有任務需要清除")
else:
    print("正在清除任務...")

    cleared_count = 0

    # 清除等待中的任務
    for job_id in queued_job_ids:
        try:
            job = queue.fetch_job(job_id)
            if job:
                job.delete()
                cleared_count += 1
                print("  ✅ 已刪除等待中的任務: {}".format(job_id))
        except Exception as e:
            print("  ⚠️ 刪除任務失敗 {}: {}".format(job_id, e))

    # 清除執行中的任務（從 registry 中移除）
    for job_id in started_job_ids:
        try:
            started_registry.remove(job_id)
            cleared_count += 1
            print("  ✅ 已從執行中註冊表移除: {}".format(job_id))
        except Exception as e:
            print("  ⚠️ 移除失敗 {}: {}".format(job_id, e))

    # 清除已完成的任務（從 registry 中移除）
    for job_id in finished_job_ids:
        try:
            finished_registry.remove(job_id)
            cleared_count += 1
            print("  ✅ 已從已完成註冊表移除: {}".format(job_id))
        except Exception as e:
            print("  ⚠️ 移除失敗 {}: {}".format(job_id, e))

    # 清除失敗的任務（從 registry 中移除）
    for job_id in failed_job_ids:
        try:
            failed_registry.remove(job_id)
            cleared_count += 1
            print("  ✅ 已從失敗註冊表移除: {}".format(job_id))
        except Exception as e:
            print("  ⚠️ 移除失敗 {}: {}".format(job_id, e))

    # 清空隊列
    queue.empty()
    print("\n✅ 已清除 {} 個任務，隊列已清空".format(cleared_count))

# 驗證清除結果
print("\n=== 驗證清除結果 ===")
queued_after = len(queue.get_job_ids(0, -1))
started_after = len(started_registry.get_job_ids(0, -1))
finished_after = len(finished_registry.get_job_ids(0, -1))
failed_after = len(failed_registry.get_job_ids(0, -1))

print("  等待中 (queued): {}".format(queued_after))
print("  執行中 (started): {}".format(started_after))
print("  已完成 (finished): {}".format(finished_after))
print("  失敗 (failed): {}".format(failed_after))

if queued_after == 0 and started_after == 0 and finished_after == 0 and failed_after == 0:
    print("\n✅ {} 隊列已完全清除".format(queue_name))
else:
    print("\n⚠️ 仍有 {} 個任務殘留".format(queued_after + started_after + finished_after + failed_after))
PYEOF
