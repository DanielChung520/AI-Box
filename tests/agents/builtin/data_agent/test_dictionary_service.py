# 代碼功能說明: DictionaryService 單元測試
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""DictionaryService 單元測試"""

from unittest.mock import MagicMock, patch

import pytest

from agents.builtin.data_agent.dictionary_service import DictionaryService


@pytest.fixture
def dictionary_service() -> DictionaryService:
    """創建 DictionaryService 實例"""
    return DictionaryService()


@pytest.mark.asyncio
async def test_create_dictionary_success(dictionary_service: DictionaryService) -> None:
    """測試創建數據字典成功"""
    mock_storage = MagicMock()
    mock_storage._ensure_bucket_exists = MagicMock()
    mock_storage.s3_client.put_object = MagicMock()

    dictionary_data = {
        "dictionary_id": "test_dict",
        "name": "Test Dictionary",
        "version": "1.0.0",
        "tables": [],
    }

    with patch.object(dictionary_service, "_get_storage", return_value=mock_storage):
        result = await dictionary_service.create("test_dict", dictionary_data)

    assert result["success"] is True
    assert result["dictionary_id"] == "test_dict"


@pytest.mark.asyncio
async def test_create_dictionary_invalid_data(dictionary_service: DictionaryService) -> None:
    """測試創建數據字典 - 無效數據"""
    invalid_data = {"name": "Test"}  # 缺少必需字段

    result = await dictionary_service.create("test_dict", invalid_data)

    assert result["success"] is False
    assert "Invalid dictionary data" in result["error"]


@pytest.mark.asyncio
async def test_get_dictionary_success(dictionary_service: DictionaryService) -> None:
    """測試查詢數據字典成功"""
    mock_storage = MagicMock()
    mock_response = MagicMock()
    mock_response["Body"].read.return_value = b'{"dictionary_id": "test_dict", "name": "Test"}'
    mock_storage.s3_client.get_object.return_value = mock_response

    with patch.object(dictionary_service, "_get_storage", return_value=mock_storage):
        result = await dictionary_service.get("test_dict")

    assert result["success"] is True
    assert "dictionary" in result


@pytest.mark.asyncio
async def test_get_dictionary_not_found(dictionary_service: DictionaryService) -> None:
    """測試查詢數據字典 - 不存在"""
    from botocore.exceptions import ClientError

    mock_storage = MagicMock()
    error_response = {"Error": {"Code": "NoSuchKey"}}
    mock_storage.s3_client.get_object.side_effect = ClientError(error_response, "GetObject")

    with patch.object(dictionary_service, "_get_storage", return_value=mock_storage):
        result = await dictionary_service.get("nonexistent")

    assert result["success"] is False
    assert "Dictionary not found" in result["error"]
