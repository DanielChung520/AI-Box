# 代碼功能說明: FastAPI Service 基礎功能整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-1.1：FastAPI Service 基礎功能測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestFastAPIService:
    """FastAPI Service 基礎功能測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        """創建異步 HTTP 客戶端"""
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_health_check(self, client: AsyncClient):
        """步驟 1: 健康檢查測試"""
        start_time = time.time()
        response = await client.get("/health")
        elapsed_ms = (time.time() - start_time) * 1000

        assert_response_success(response)
        data = response.json()
        assert data.get("data", {}).get("status") == "healthy"
        assert elapsed_ms < 100, f"健康檢查響應時間 {elapsed_ms}ms 超過 100ms"

    async def test_readiness_check(self, client: AsyncClient):
        """步驟 2: 就緒檢查測試"""
        response = await client.get("/ready")

        assert_response_success(response)
        data = response.json()
        assert data.get("data", {}).get("status") == "ready"

    async def test_api_documentation(self, client: AsyncClient):
        """步驟 3: API 文檔訪問測試"""
        # 測試 Swagger UI
        response = await client.get("/docs")
        assert response.status_code == 200

        # 測試 ReDoc
        response = await client.get("/redoc")
        assert response.status_code == 200

    async def test_version_info(self, client: AsyncClient):
        """步驟 4: 版本信息查詢"""
        response = await client.get("/version")

        assert_response_success(response)
        data = response.json()
        assert "version" in data
        assert "major" in data
        assert "minor" in data
        assert "patch" in data

    async def test_middleware_request_id(self, client: AsyncClient):
        """步驟 5: Request ID 中間件測試"""
        response = await client.get("/health")

        assert_response_success(response)
        # 檢查 Request ID 頭部
        request_id = response.headers.get("X-Request-ID")
        assert request_id is not None, "Request ID 未在響應頭中返回"

    async def test_middleware_error_handling(self, client: AsyncClient):
        """步驟 5: 錯誤處理中間件測試"""
        # 發送無效請求
        response = await client.get("/nonexistent-endpoint")

        assert response.status_code == 404, "應返回 404 狀態碼"

    async def test_middleware_cors(self, client: AsyncClient):
        """步驟 5: CORS 中間件測試"""
        # 發送 OPTIONS 請求測試 CORS
        response = await client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        # CORS 預檢請求應該返回 200
        assert response.status_code in [200, 204]
        # 檢查 CORS 頭部
        assert (
            "Access-Control-Allow-Origin" in response.headers
            or response.status_code == 204
        )
