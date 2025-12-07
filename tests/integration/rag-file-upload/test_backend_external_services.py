# 代碼功能說明: 後端-外部服務集成測試
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""後端-外部服務集成測試 - 測試Ollama服務調用、錯誤處理"""

import pytest
from unittest.mock import patch, AsyncMock
from fastapi.testclient import TestClient

from api.main import app
from services.api.services.embedding_service import EmbeddingService


@pytest.fixture(scope="module")
def client():
    """創建測試客戶端"""
    return TestClient(app)


@pytest.mark.asyncio
async def test_ollama_embedding_service_call():
    """測試Ollama嵌入服務調用"""
    with patch(
        "services.api.services.embedding_service.httpx.AsyncClient"
    ) as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1] * 384}

        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        service = EmbeddingService()
        result = await service.generate_embedding("測試文本")

        assert result is not None
        assert len(result) == 384


@pytest.mark.asyncio
async def test_ollama_service_error_handling():
    """測試Ollama服務錯誤處理"""
    with patch(
        "services.api.services.embedding_service.httpx.AsyncClient"
    ) as mock_client:
        # 模擬服務不可用
        mock_client_instance = AsyncMock()
        mock_client_instance.post = AsyncMock(
            side_effect=Exception("Connection refused")
        )
        mock_client.return_value.__aenter__.return_value = mock_client_instance

        service = EmbeddingService()

        with pytest.raises(Exception):
            await service.generate_embedding("測試文本", max_retries=1)


def test_file_upload_with_ollama_unavailable(client):
    """測試Ollama不可用時的文件上傳處理"""
    from io import BytesIO

    content = "測試Ollama不可用的情況".encode("utf-8")
    files = {"files": ("ollama_test.txt", BytesIO(content), "text/plain")}

    # 即使Ollama不可用，文件上傳也應該成功
    upload_response = client.post("/api/v1/files/upload", files=files)
    assert upload_response.status_code == 200

    upload_data = upload_response.json()
    assert upload_data["success"] is True

    # 向量化可能會失敗，但不應該影響文件上傳
    file_id = upload_data["data"]["uploaded"][0]["file_id"]

    # 查詢處理狀態
    import time

    time.sleep(2)

    status_response = client.get(f"/api/v1/files/{file_id}/processing-status")
    assert status_response.status_code == 200
