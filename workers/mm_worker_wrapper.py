#!/usr/bin/env python3
"""
MM-Agent RQ Worker Wrapper
確保 datalake-system 在 Python 路徑中，然後啟動 RQ Worker
"""

import os
import sys
from pathlib import Path

# 專案根目錄
PROJECT_ROOT = Path(__file__).parent.parent
DATALAKE_SYSTEM = PROJECT_ROOT / "datalake-system"

# 添加 datalake-system 到 sys.path
if str(DATALAKE_SYSTEM) not in sys.path:
    sys.path.insert(0, str(DATALAKE_SYSTEM))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# 打印路徑信息（除錯用）
print(f"[MM-Worker-Wrapper] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[MM-Worker-Wrapper] DATALAKE_SYSTEM: {DATALAKE_SYSTEM}")
print(f"[MM-Worker-Wrapper] sys.path: {sys.path[:3]}...")

# 驗證 datalake-system 可導入
try:
    import mm_agent.chain.react_executor
    import mm_agent.chain.rq_task  # 預先導入 RQ 任務模組

    print(f"[MM-Worker-Wrapper] ✅ datalake-system.mm_agent 可導入")
    print(f"[MM-Worker-Wrapper] ✅ rq_task 模組已導入")
except ImportError as e:
    print(f"[MM-Worker-Wrapper] ❌ 導入失敗: {e}")
    sys.exit(1)


# 動態修改 Worker 命令的函數
def run_worker():
    """運行 RQ Worker"""
    import argparse
    from redis import Redis
    from rq import Worker

    parser = argparse.ArgumentParser(description="MM-Agent RQ Worker")
    parser.add_argument("--host", default="localhost", help="Redis host")
    parser.add_argument("--port", type=int, default=6379, help="Redis port")
    parser.add_argument("--db", type=int, default=0, help="Redis db")
    parser.add_argument("--password", default=None, help="Redis password")
    parser.add_argument("queues", nargs="+", help="Queue names")
    parser.add_argument("--name", default=None, help="Worker name")
    parser.add_argument("--url", default=None, help="Redis URL")

    args = parser.parse_args()

    # 構建 Redis URL
    if args.url:
        redis_url = args.url
    else:
        redis_password = args.password if args.password else ""
        if redis_password:
            redis_url = f"redis://:{redis_password}@{args.host}:{args.port}/{args.db}"
        else:
            redis_url = f"redis://{args.host}:{args.port}/{args.db}"

    print(f"[MM-Worker-Wrapper] 啟動 Worker...")
    print(f"[MM-Worker-Wrapper] Redis URL: {redis_url}")
    print(f"[MM-Worker-Wrapper] Queues: {args.queues}")
    print(f"[MM-Worker-Wrapper] Worker name: {args.name}")

    # 連接 Redis
    conn = Redis.from_url(redis_url)

    # 創建 Worker
    worker = Worker(
        args.queues,
        connection=conn,
        name=args.name,
        default_worker_ttl=1800,  # 30 分鐘
    )

    print(f"[MM-Worker-Wrapper] Worker PID: {os.getpid()}")
    print(f"[MM-Worker-Wrapper] 開始處理任務...")

    # 啟動 Worker
    worker.work(with_scheduler=True)


if __name__ == "__main__":
    run_worker()
