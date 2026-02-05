# 代碼功能說明: 驗證 Task Cleanup Agent 的 AOGA 合規性
# 創建日期: 2026-01-23

import asyncio
import sys
import os

# 加入路徑以導入模組
sys.path.append(os.getcwd())

from agents.builtin.task_cleanup_agent.agent import TaskCleanupAgent
from database.arangodb import ArangoDBClient


async def verify_aoga():
    agent = TaskCleanupAgent()
    user_id = "daniel@test.com"

    print("\n=== Phase 1: Analyze (Reasoning Only) ===")
    res1 = await agent.handle_request("analyze", {"user_id": user_id, "actor": "admin_user"})
    print(f"Success: {res1.success}")
    print(f"Audit Record ID: {res1.audit_record_id}")
    print(f"Message: {res1.message}")

    print("\n=== Phase 2: Plan (Risk Gating Check) ===")
    res2 = await agent.handle_request("plan", {"user_id": user_id, "actor": "admin_user"})
    print(f"Success: {res2.success}")
    print(f"Risk Level: {res2.analysis.risk_level if res2.analysis else 'N/A'}")
    print(f"Audit Record ID: {res2.audit_record_id}")

    print("\n=== Phase 3: Cleanup (Execution without Token) ===")
    # 模擬高風險，不帶 token 應失敗
    res3 = await agent.handle_request("cleanup", {"user_id": user_id, "actor": "admin_user"})
    print(f"Success: {res3.success} (Expected False if high risk)")
    print(f"Message: {res3.message}")

    print("\n=== Phase 4: Cleanup (Execution with Token) ===")
    # 帶上 token 應成功
    res4 = await agent.handle_request(
        "cleanup", {"user_id": user_id, "actor": "admin_user", "approval_token": "ADMIN_CONFIRMED"}
    )
    print(f"Success: {res4.success}")
    print(f"Audit Record ID: {res4.audit_record_id}")
    print(f"Message: {res4.message}")

    print("\n=== Phase 5: Verify Audit Log (Immutability & Hash) ===")
    client = ArangoDBClient()
    coll = client.db.collection("system_audit_logs")
    record = coll.get(res4.audit_record_id)
    if record:
        print(f"Audit Record Found: {record['_key']}")
        print(f"Content Hash: {record.get('content_hash')}")
        print(f"Execution Result: {record.get('execution', {}).get('result')}")
        print(
            f"Deleted Tasks Count: {record.get('execution', {}).get('details', {}).get('user_tasks')}"
        ),
    else:
        print("Error: Audit record not found in database")


if __name__ == "__main__":
    asyncio.run(verify_aoga())
