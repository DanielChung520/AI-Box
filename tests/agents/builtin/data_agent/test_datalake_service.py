# 代碼功能說明: DatalakeService 單元測試
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""DatalakeService 單元測試"""

from unittest.mock import MagicMock, patch

import pytest

from agents.builtin.data_agent.datalake_service import DatalakeService


@pytest.fixture
def datalake_service() -> DatalakeService:
    """創建 DatalakeService 實例"""
    return DatalakeService()


@pytest.mark.asyncio
async def test_query_exact_success(datalake_service: DatalakeService) -> None:
    """測試精確查詢成功"""
    # Mock S3 client
    mock_storage = MagicMock()
    mock_response = MagicMock()
    mock_response["Body"].read.return_value = b'{"part_number": "ABC-123", "name": "Test Part"}'
    mock_storage.s3_client.get_object.return_value = mock_response

    with patch.object(datalake_service, "_get_storage", return_value=mock_storage):
        result = await datalake_service._query_exact(mock_storage, "bucket", "key.json")

    assert result["success"] is True
    assert result["row_count"] == 1
    assert result["query_type"] == "exact"


@pytest.mark.asyncio
async def test_query_exact_file_not_found(datalake_service: DatalakeService) -> None:
    """測試精確查詢文件不存在"""
    from botocore.exceptions import ClientError

    mock_storage = MagicMock()
    error_response = {"Error": {"Code": "NoSuchKey"}}
    mock_storage.s3_client.get_object.side_effect = ClientError(error_response, "GetObject")

    with patch.object(datalake_service, "_get_storage", return_value=mock_storage):
        result = await datalake_service._query_exact(mock_storage, "bucket", "key.json")

    assert result["success"] is False
    assert "File not found" in result["error"]


@pytest.mark.asyncio
async def test_query_fuzzy_success(datalake_service: DatalakeService) -> None:
    """測試模糊查詢成功"""
    mock_storage = MagicMock()
    mock_list_response = {
        "Contents": [
            {"Key": "parts/ABC-123.json"},
            {"Key": "parts/ABC-124.json"},
        ]
    }
    mock_storage.s3_client.list_objects_v2.return_value = mock_list_response

    mock_get_response = MagicMock()
    mock_get_response["Body"].read.return_value = b'{"part_number": "ABC-123"}'
    mock_storage.s3_client.get_object.return_value = mock_get_response

    with patch.object(datalake_service, "_get_storage", return_value=mock_storage):
        result = await datalake_service._query_fuzzy(mock_storage, "bucket", "parts/", None)

    assert result["success"] is True
    assert result["query_type"] == "fuzzy"


def test_apply_filters(datalake_service: DatalakeService) -> None:
    """測試應用過濾條件"""
    rows = [
        {"part_number": "ABC-123", "stock": 10},
        {"part_number": "ABC-124", "stock": 20},
        {"part_number": "ABC-125", "stock": 15},
    ]

    filters = {"stock": {"gte": 15}}
    filtered = datalake_service._apply_filters(rows, filters)

    assert len(filtered) == 2
    assert all(row["stock"] >= 15 for row in filtered)
