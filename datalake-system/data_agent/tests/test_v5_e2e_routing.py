# 代碼功能說明: V5 E2E 路由驗證測試
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

import socket
import subprocess
import time
from collections.abc import Generator
from typing import Any, Dict

import httpx
import pytest

QDRANT_COLLECTION_URL = "http://localhost:6333/collections/jp_intents"
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"


def _extract_sql(payload: Dict[str, Any]) -> str:
    sql = payload.get("sql")
    if isinstance(sql, str):
        return sql
    result = payload.get("result")
    if isinstance(result, dict) and isinstance(result.get("sql"), str):
        return result["sql"]
    details = payload.get("details")
    if isinstance(details, dict) and isinstance(details.get("sql"), str):
        return details["sql"]
    return ""


def _post_nlq(client: httpx.Client, task_id: str, nlq: str) -> Dict[str, Any]:
    req = {
        "task_id": task_id,
        "task_type": "schema_driven_query",
        "task_data": {"nlq": nlq},
    }
    resp = client.post("/v5/execute", json=req)
    assert resp.status_code == 200, f"HTTP {resp.status_code}, body={resp.text}"
    data = resp.json()
    print(f"[E2E] task_id={task_id} nlq={nlq} response={data}")
    return data


@pytest.fixture(scope="module")
def e2e_client() -> Generator[httpx.Client, None, None]:
    client = httpx.Client(timeout=120.0)

    try:
        health = client.get("http://localhost:8004/api/v1/data-agent/v5/health")
        if health.status_code != 200:
            pytest.skip(f"Data-Agent v5 not ready: status={health.status_code}, body={health.text}")
    except Exception as error:
        pytest.skip(f"Data-Agent v5 not reachable: {error}")

    try:
        qdrant = client.get(QDRANT_COLLECTION_URL)
        if qdrant.status_code != 200:
            pytest.skip(
                f"Qdrant jp_intents not ready: status={qdrant.status_code}, body={qdrant.text}"
            )
    except Exception as error:
        pytest.skip(f"Qdrant not reachable: {error}")

    try:
        ollama = client.get(OLLAMA_TAGS_URL)
        if ollama.status_code != 200:
            pytest.skip(f"Ollama not ready: status={ollama.status_code}, body={ollama.text}")
    except Exception as error:
        pytest.skip(f"Ollama not reachable: {error}")

    probe = client.get("http://localhost:8004/api/v1/data-agent/v5/health")
    if probe.status_code != 200:
        pytest.skip("Data-Agent v5 health probe failed")

    test_port = 8014
    proc = subprocess.Popen(
        [
            "python3",
            "-m",
            "uvicorn",
            "data_agent.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(test_port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    started = False
    for _ in range(40):
        time.sleep(0.5)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            started = sock.connect_ex(("127.0.0.1", test_port)) == 0
        finally:
            sock.close()
        if started:
            break

    if not started:
        proc.terminate()
        pytest.skip("Cannot start isolated Data-Agent v5 server on port 8014")

    isolated = httpx.Client(
        base_url=f"http://127.0.0.1:{test_port}/api/v1/data-agent", timeout=120.0
    )

    try:
        health = isolated.get("/v5/health")
        if health.status_code != 200:
            pytest.skip(
                f"Isolated Data-Agent v5 not ready: status={health.status_code}, body={health.text}"
            )
    except Exception as error:
        proc.terminate()
        pytest.skip(f"Isolated Data-Agent v5 not reachable: {error}")

    yield isolated

    isolated.close()
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    client.close()


class TestV5E2ERouting:
    def test_simple_query_uses_raw_table(self, e2e_client: httpx.Client) -> None:
        payload = _post_nlq(e2e_client, "e2e-test-001", "查詢料號NI001的庫存")
        assert ("success" in payload) or (
            "status" in payload
        ), f"Unexpected response body: {payload}"

        sql = _extract_sql(payload).lower()
        assert sql, f"SQL is empty, response={payload}"
        assert "mart_" not in sql, f"Expected raw SQL, got={sql}, response={payload}"
        assert (
            "read_parquet" in sql or "inag" in sql
        ), f"Expected read_parquet or INAG in SQL, got={sql}, response={payload}"

    def test_complex_query_uses_mart_table(self, e2e_client: httpx.Client) -> None:
        payload = _post_nlq(e2e_client, "e2e-test-002", "各倉庫庫存數量前10名排名")
        assert ("success" in payload) or (
            "status" in payload
        ), f"Unexpected response body: {payload}"

        sql = _extract_sql(payload).lower()
        assert sql, f"SQL is empty, response={payload}"
        assert "mart_" in sql, f"Expected mart SQL, got={sql}, response={payload}"

    def test_qiantian_not_complex(self, e2e_client: httpx.Client) -> None:
        payload = _post_nlq(e2e_client, "e2e-test-003", "前天的出貨記錄")
        assert ("success" in payload) or (
            "status" in payload
        ), f"Unexpected response body: {payload}"

        sql = _extract_sql(payload).lower()
        assert sql, f"SQL is empty, response={payload}"
        assert "mart_" not in sql, f"Expected raw SQL for 前天 query, got={sql}, response={payload}"

    def test_no_mart_intent_uses_raw_table(self, e2e_client: httpx.Client) -> None:
        payload = _post_nlq(e2e_client, "e2e-test-004", "查詢品質檢驗結果")
        assert ("success" in payload) or (
            "status" in payload
        ), f"Unexpected response body: {payload}"

        sql = _extract_sql(payload).lower()
        assert sql, f"SQL is empty, response={payload}"
        assert (
            "mart_" not in sql
        ), f"Expected raw SQL for quality query, got={sql}, response={payload}"

    def test_low_confidence_returns_valid_response(self, e2e_client: httpx.Client) -> None:
        payload = _post_nlq(e2e_client, "e2e-test-005", "幫我看看")

        assert payload, "Response payload is empty"
        assert ("success" in payload) or (
            "status" in payload
        ), f"Invalid response format: {payload}"

        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and metadata.get("model_used"):
            assert "gpt-oss:120b" in str(
                metadata.get("model_used")
            ), f"Expected big model for low confidence, response={payload}"
