# 代碼功能說明: ChromaDB 向量資料庫整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-1.3：ChromaDB 向量資料庫整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import (
    assert_response_success,
)


@pytest.mark.integration
@pytest.mark.asyncio
class TestChromaDBIntegration:
    """ChromaDB 向量資料庫整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    @pytest.fixture(scope="function")
    def test_collection_name(self) -> str:
        return f"test_collection_{int(time.time())}"

    async def test_chromadb_connection(self):
        """步驟 1: ChromaDB 連接測試"""
        try:
            from database.chromadb import ChromaDBClient

            client = ChromaDBClient()
            collections = client.list_collections()
            assert collections is not None
        except ImportError:
            pytest.skip("ChromaDB 客戶端未安裝")
        except Exception as e:
            pytest.fail(f"ChromaDB 連接失敗: {str(e)}")

    async def test_create_collection(
        self, client: AsyncClient, test_collection_name: str
    ):
        """步驟 2: 集合創建測試"""
        response = await client.post(
            "/api/v1/chromadb/collections",
            json={"name": test_collection_name},
        )
        assert response.status_code in [
            200,
            201,
            409,
        ], f"集合創建失敗: {response.status_code} - {response.text}"

        response = await client.post(
            "/api/v1/chromadb/collections",
            json={"name": test_collection_name},
        )
        assert response.status_code in [
            200,
            201,
            409,
        ], f"集合創建失敗: {response.status_code} - {response.text}"

    async def test_vector_search(self, client: AsyncClient, test_collection_name: str):
        """步驟 3: 向量檢索測試"""
        # 確保集合存在
        await client.post(
            "/api/v1/chromadb/collections",
            json={"name": test_collection_name},
        )

        start_time = time.time()
        test_embedding = [0.1] * 384
        response = await client.post(
            f"/api/v1/chromadb/collections/{test_collection_name}/query",
            json={"query_embeddings": [test_embedding], "n_results": 5},
        )
        elapsed_ms = (time.time() - start_time) * 1000
        assert_response_success(response)
        assert elapsed_ms < 20, f"向量檢索延遲 {elapsed_ms}ms 超過 20ms"
