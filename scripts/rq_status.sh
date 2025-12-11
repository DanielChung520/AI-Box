#!/bin/bash
# 代碼功能說明: RQ 隊列狀態查詢腳本
# 創建日期: 2025-12-10
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-10

set -e

# 顏色定義
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
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

echo -e "${BLUE}=== RQ 隊列狀態查詢 ===${NC}"
echo ""

# 執行 Python 查詢腳本
"$PYTHON_CMD" << 'PYTHON_EOF'
import sys
sys.path.insert(0, '.')

from database.rq.monitor import (
    get_all_queues,
    get_queue_stats,
    get_all_queues_stats,
    get_workers_info,
)

print("=" * 70)
print("RQ 隊列狀態")
print("=" * 70)

# 1. 查詢所有隊列
print("\n📋 所有隊列:")
print("-" * 70)
queues = get_all_queues()
if queues:
    print(f"找到 {len(queues)} 個隊列:")
    for queue_name in queues:
        print(f"  ✅ {queue_name}")
else:
    print("  未找到任何隊列（如果還沒有提交任務，這是正常的）")

# 2. 查詢預定義隊列的統計
print("\n📊 隊列統計:")
print("-" * 70)
predefined_queues = ["file_processing", "vectorization", "kg_extraction"]
has_data = False
for queue_name in predefined_queues:
    stats = get_queue_stats(queue_name)
    if "error" not in stats:
        total = stats.get('total', 0)
        if total > 0 or True:  # 總是顯示
            has_data = True
            print(f"\n  {queue_name}:")
            print(f"    等待中: {stats.get('queued', 0)}")
            print(f"    執行中: {stats.get('started', 0)}")
            print(f"    已完成: {stats.get('finished', 0)}")
            print(f"    失敗: {stats.get('failed', 0)}")
            print(f"    總計: {stats.get('total', 0)}")

if not has_data:
    print("  所有隊列為空（這是正常的，如果還沒有提交任務）")

# 3. 查詢 Worker 信息
print("\n👷 Worker 信息:")
print("-" * 70)
workers = get_workers_info()
if workers:
    print(f"找到 {len(workers)} 個 Worker:")
    for worker in workers:
        print(f"\n  ✅ {worker['name']}")
        print(f"    狀態: {worker['state']}")
        print(f"    隊列: {', '.join(worker['queues']) if worker['queues'] else '無'}")
        print(f"    當前任務: {worker['current_job_id'] or '無'}")
        if worker.get('birth_date'):
            print(f"    啟動時間: {worker['birth_date']}")
else:
    print("  未找到運行中的 Worker")
    print("  提示: 使用 ./scripts/start_rq_worker.sh file_processing 啟動 Worker")

print("\n" + "=" * 70)
print("💡 提示:")
print("  - 使用 API: GET /api/v1/rq/queues/stats 查看詳細統計")
print("  - 使用 API: GET /api/v1/rq/workers 查看 Worker 詳情")
print("  - 使用 API: GET /api/v1/rq/queues/{queue_name}/jobs 查看任務列表")
print("=" * 70)
PYTHON_EOF
