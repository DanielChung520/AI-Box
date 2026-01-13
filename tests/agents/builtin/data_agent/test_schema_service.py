# 代碼功能說明: SchemaService 單元測試
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""SchemaService 單元測試"""

from unittest.mock import MagicMock, patch

import pytest

from agents.builtin.data_agent.schema_service import SchemaService


@pytest.fixture
def schema_service() -> SchemaService:
    """創建 SchemaService 實例"""
    return SchemaService()


@pytest.mark.asyncio
async def test_create_schema_success(schema_service: SchemaService) -> None:
    """測試創建 Schema 成功"""
    mock_storage = MagicMock()
    mock_storage._ensure_bucket_exists = MagicMock()
    mock_storage.s3_client.put_object = MagicMock()

    schema_data = {
        "json_schema": {
            "type": "object",
            "properties": {
                "part_number": {"type": "string"},
                "name": {"type": "string"},
            },
            "required": ["part_number"],
        }
    }

    with patch.object(schema_service, "_get_storage", return_value=mock_storage):
        result = await schema_service.create("test_schema", schema_data)

    assert result["success"] is True
    assert result["schema_id"] == "test_schema"


@pytest.mark.asyncio
async def test_create_schema_invalid_json_schema(schema_service: SchemaService) -> None:
    """測試創建 Schema - 無效的 JSON Schema"""
    invalid_schema_data = {
        "json_schema": {
            "type": "invalid_type",  # 無效的類型
        }
    }

    result = await schema_service.create("test_schema", invalid_schema_data)

    assert result["success"] is False
    assert "Invalid JSON Schema" in result["error"]


@pytest.mark.asyncio
async def test_validate_data_success(schema_service: SchemaService) -> None:
    """測試數據驗證成功"""
    mock_storage = MagicMock()
    mock_response = MagicMock()
    mock_response[
        "Body"
    ].read.return_value = b'{"json_schema": {"type": "object", "properties": {"part_number": {"type": "string"}}, "required": ["part_number"]}}'
    mock_storage.s3_client.get_object.return_value = mock_response

    data = [{"part_number": "ABC-123"}]

    with patch.object(schema_service, "_get_storage", return_value=mock_storage):
        result = await schema_service.validate_data(data, "test_schema")

    assert result["success"] is True
    assert result["valid"] is True
    assert len(result["issues"]) == 0


@pytest.mark.asyncio
async def test_validate_data_failed(schema_service: SchemaService) -> None:
    """測試數據驗證失敗"""
    mock_storage = MagicMock()
    mock_response = MagicMock()
    mock_response[
        "Body"
    ].read.return_value = b'{"json_schema": {"type": "object", "properties": {"part_number": {"type": "string"}}, "required": ["part_number"]}}'
    mock_storage.s3_client.get_object.return_value = mock_response

    data = [{}]  # 缺少必需字段

    with patch.object(schema_service, "_get_storage", return_value=mock_storage):
        result = await schema_service.validate_data(data, "test_schema")

    assert result["success"] is True
    assert result["valid"] is False
    assert len(result["issues"]) > 0
