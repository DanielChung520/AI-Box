# 代碼功能說明: Data-Agent → DuckDB → SeaweedFS 端到端 E2E 測試
# 創建日期: 2026-01-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""Data-Agent → DuckDB → SeaweedFS 端到端 E2E 測試腳本

執行順序：L1 SeaweedFS → L2 DuckDB → L3 DatalakeService → L4 Data-Agent
參考文檔：.ds-docs/Datalake/Data-Agent-DuckDB-SeaweedFS-E2E測試計劃.md

執行方式：
  cd /home/daniel/ai-box/datalake-system
  source venv/bin/activate
  python tests/data_agent/e2e_test_full.py
"""

import asyncio
import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

# 添加 datalake-system 到路徑
datalake_root = Path(__file__).resolve().parent.parent.parent
if str(datalake_root) not in sys.path:
    sys.path.insert(0, str(datalake_root))


def run_l1_seaweedfs() -> tuple[bool, str]:
    """L1: SeaweedFS 層測試"""
    try:
        import boto3
        import pandas as pd
        from io import BytesIO

        s3 = boto3.client(
            "s3",
            endpoint_url="http://localhost:8334",
            aws_access_key_id="admin",
            aws_secret_access_key="admin123",
            region_name="us-east-1",
        )

        # L1-002: Bucket 存在
        buckets = s3.list_buckets()
        if not any(b["Name"] == "tiptop-raw" for b in buckets["Buckets"]):
            return False, "Bucket tiptop-raw 不存在"

        # L1-003: img_file Parquet 存在
        objs = s3.list_objects_v2(Bucket="tiptop-raw", Prefix="raw/v1/img_file/")
        keys = [o["Key"] for o in objs.get("Contents", []) if o["Key"].endswith(".parquet")]
        if not keys:
            return False, "img_file Parquet 不存在，請執行 master_data_gen.py"

        # L1-004: 讀取 Parquet
        resp = s3.get_object(Bucket="tiptop-raw", Key=keys[0])
        df = pd.read_parquet(BytesIO(resp["Body"].read()))
        if len(df) == 0:
            return False, "Parquet 無數據"

        return True, f"L1 通過: img_file 共 {len(df)} 筆"
    except Exception as e:
        return False, f"L1 失敗: {e}"


def run_l2_duckdb() -> tuple[bool, str]:
    """L2: DuckDB 層測試"""
    try:
        import duckdb

        con = duckdb.connect(":memory:")
        con.execute("""
            SET s3_endpoint = 'localhost:8334';
            SET s3_access_key_id = 'admin';
            SET s3_secret_access_key = 'admin123';
            SET s3_use_ssl = false;
            SET s3_url_style = 'path';
        """)

        path = "s3://tiptop-raw/raw/v1/img_file/**/*.parquet"

        # L2-001: 基本 SELECT
        r = con.execute(
            f"SELECT * FROM read_parquet('{path}', hive_partitioning=true) LIMIT 5"
        ).fetchall()
        if len(r) > 5:
            return False, "L2-001 失敗"

        # L2-003: SUM 聚合
        r = con.execute(
            f"SELECT SUM(img10) FROM read_parquet('{path}', hive_partitioning=true) "
            "WHERE img01='10-0001'"
        ).fetchone()
        if r[0] is None:
            return False, "L2-003 SUM 失敗"

        return True, "L2 通過"
    except Exception as e:
        return False, f"L2 失敗: {e}"


async def run_l3_datalake_service() -> tuple[bool, str]:
    """L3: DatalakeService 層測試"""
    try:
        from data_agent.datalake_service import DatalakeService

        svc = DatalakeService()
        r = await svc.query_sql("SELECT * FROM img_file LIMIT 5", max_rows=10)
        if not r.get("success"):
            return False, f"L3-001 失敗: {r.get('error')}"
        if r.get("query_type") != "sql_duckdb":
            return False, f"L3 未使用 DuckDB: {r.get('query_type')}"
        return True, f"L3 通過: {r.get('row_count', 0)} 筆"
    except Exception as e:
        return False, f"L3 失敗: {e}"


async def run_l4_data_agent() -> tuple[bool, str]:
    """L4: Data-Agent 端到端測試（text_to_sql → execute_sql_on_datalake）"""
    try:
        from agents.services.protocol.base import AgentServiceRequest
        from data_agent.agent import DataAgent

        agent = DataAgent()

        # E2E: text_to_sql
        r1 = await agent.execute(
            AgentServiceRequest(
                task_id="e2e-test-001",
                task_type="text_to_sql",
                task_data={
                    "action": "text_to_sql",
                    "natural_language": "查詢料號為 10-0001 的庫存記錄",
                },
            )
        )
        if r1.status != "completed":
            return False, f"text_to_sql 失敗: {r1.error}"

        result = r1.result or {}
        sql = result.get("result", {}).get("sql_query") or result.get("sql_query") or ""
        if not sql:
            return False, "text_to_sql 未返回 SQL"

        # E2E: execute_sql_on_datalake
        r2 = await agent.execute(
            AgentServiceRequest(
                task_id="e2e-test-002",
                task_type="query",
                task_data={
                    "action": "execute_sql_on_datalake",
                    "sql_query_datalake": sql,
                    "max_rows": 100,
                },
            )
        )
        if r2.status != "completed":
            return False, f"execute_sql_on_datalake 失敗: {r2.error}"

        r2_result = r2.result or {}
        if not r2_result.get("success"):
            return False, f"execute_sql_on_datalake 錯誤: {r2_result.get('error')}"

        rows = r2_result.get("result", {}).get("rows", []) or r2_result.get("rows", [])
        return True, f"L4 通過: 返回 {len(rows)} 筆"
    except Exception as e:
        return False, f"L4 失敗: {e}"


async def main() -> int:
    """執行全部 E2E 測試"""
    print("=" * 60)
    print("Data-Agent → DuckDB → SeaweedFS E2E 測試")
    print("=" * 60)

    results: list[tuple[str, bool, str]] = []

    # L1
    ok, msg = run_l1_seaweedfs()
    results.append(("L1 SeaweedFS", ok, msg))
    print(f"[{'✓' if ok else '✗'}] L1 SeaweedFS: {msg}")

    if not ok:
        print("\nL1 失敗，跳過後續測試。請檢查 SeaweedFS 與測試數據。")
        return 1

    # L2
    ok, msg = run_l2_duckdb()
    results.append(("L2 DuckDB", ok, msg))
    print(f"[{'✓' if ok else '✗'}] L2 DuckDB: {msg}")

    if not ok:
        print("\nL2 失敗，跳過後續測試。")
        return 1

    # L3
    ok, msg = await run_l3_datalake_service()
    results.append(("L3 DatalakeService", ok, msg))
    print(f"[{'✓' if ok else '✗'}] L3 DatalakeService: {msg}")

    if not ok:
        print("\nL3 失敗，跳過 L4。")
        return 1

    # L4（需 LLM，可能較慢）
    print("\nL4 Data-Agent E2E（需 LLM，請稍候）...")
    ok, msg = await run_l4_data_agent()
    results.append(("L4 Data-Agent E2E", ok, msg))
    print(f"[{'✓' if ok else '✗'}] L4 Data-Agent E2E: {msg}")

    # 摘要
    passed = sum(1 for _, o, _ in results if o)
    total = len(results)
    print("\n" + "=" * 60)
    print(f"通過: {passed}/{total}")
    print("=" * 60)

    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
