#!/usr/bin/env python3
"""
測試 MM-Agent RQ 任務交付
"""

import sys
import time

sys.path.insert(0, "/home/daniel/ai-box/datalake-system")

from mm_agent.chain.react_executor import enqueue_rq_task


def test_rq_delivery():
    print("=" * 60)
    print("測試 MM-Agent RQ 任務交付")
    print("=" * 60)

    # 建立測試參數
    session_id = f"test_session_{int(time.time())}"
    step_id = 1
    action_type = "test_action"
    instruction = "這是一個測試任務"
    parameters = {"test_key": "test_value"}
    total_steps = 1

    print(f"\n📤 交付 RQ 任務...")
    print(f"  Session ID: {session_id}")
    print(f"  Step ID: {step_id}")
    print(f"  Action: {action_type}")

    # 交付任務
    job_id = enqueue_rq_task(
        session_id=session_id,
        step_id=step_id,
        action_type=action_type,
        instruction=instruction,
        parameters=parameters,
        total_steps=total_steps,
    )

    print(f"\n✅ 任務已交付!")
    print(f"  Job ID: {job_id}")

    # 等待一下讓 Worker 處理
    print(f"\n⏳ 等待 Worker 處理 (5 秒)...")
    time.sleep(5)

    # 檢查任務狀態
    from redis import Redis
    from rq.job import Job

    try:
        rq_conn = Redis(host="localhost", port=6379, db=0)
        job = Job.fetch(job_id, connection=rq_conn)
        print(f"\n  任務狀態:")
        print(f"    ID: {job.id}")
        print(f"    Status: {job.get_status()}")
        print(f"    Result: {job.result}")
    except Exception as e:
        print(f"  無法獲取任務詳情: {e}")

    print("\n" + "=" * 60)
    print("測試完成")
    print("=" * 60)


if __name__ == "__main__":
    test_rq_delivery()
