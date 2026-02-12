#!/usr/bin/env python3
"""
MM-Agent RQ Task Worker
专门处理 agent_todo 队列的任务
"""

import os
import sys
from pathlib import Path

# 添加项目路径
PROJECT_ROOT = Path(__file__).parent.parent
DATALAKE_SYSTEM = PROJECT_ROOT / "datalake-system"

if str(DATALAKE_SYSTEM) not in sys.path:
    sys.path.insert(0, str(DATALAKE_SYSTEM))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

print(f"[RQ-Task-Worker] PROJECT_ROOT: {PROJECT_ROOT}")
print(f"[RQ-Task-Worker] DATALAKE_SYSTEM: {DATALAKE_SYSTEM}")

# 预先导入所有需要的模块
try:
    import mm_agent.chain.rq_task as rq_task
    from mm_agent.chain.rq_task import execute_agent_todo_sync
    print(f"[RQ-Task-Worker] ✅ mm_agent.chain.rq_task 导入成功")
    print(f"[RQ-Task-Worker] ✅ execute_agent_todo_sync: {execute_agent_todo_sync}")
except ImportError as e:
    print(f"[RQ-Task-Worker] ❌ 导入失败: {e}")
    sys.exit(1)

# 启动 Worker
if __name__ == "__main__":
    import argparse
    from redis import Redis
    from rq import Worker

    parser = argparse.ArgumentParser(description="MM-Agent RQ Task Worker")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=6379)
    parser.add_argument("--name", default=None)
    parser.add_argument("queues", nargs="+")

    args = parser.parse_args()

    redis_url = f"redis://{args.host}:{args.port}/0"
    conn = Redis.from_url(redis_url)

    worker = Worker(
        args.queues,
        connection=conn,
        name=args.name,
        default_worker_ttl=1800,
    )

    print(f"[RQ-Task-Worker] 启动: {args.name}, 队列: {args.queues}")
    worker.work(with_scheduler=True)
