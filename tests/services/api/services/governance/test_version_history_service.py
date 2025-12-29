# 代碼功能說明: SeaweedFS 版本歷史服務單元測試
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 版本歷史服務單元測試 - 測試版本歷史記錄服務"""

import json
from unittest.mock import MagicMock, Mock

import pytest
from botocore.exceptions import ClientError

from services.api.models.version_history import VersionHistoryCreate
from services.api.services.governance.version_history_service import SeaweedFSVersionHistoryService
from storage.s3_storage import S3FileStorage


class TestSeaweedFSVersionHistoryService:
    """SeaweedFSVersionHistoryService 測試類"""

    @pytest.fixture
    def mock_storage(self):
        """創建模擬 S3FileStorage"""
        storage = MagicMock(spec=S3FileStorage)
        storage.s3_client = MagicMock()
        storage.bucket = "bucket-version-history"
        return storage

    @pytest.fixture
    def version_history_service(self, mock_storage):
        """創建 SeaweedFSVersionHistoryService 實例"""
        mock_storage.s3_client.head_bucket.return_value = None
        return SeaweedFSVersionHistoryService(storage=mock_storage)

    def test_get_version_file_path(self, version_history_service):
        """測試版本文件路徑生成"""
        file_path = version_history_service._get_version_file_path("ontologies", "ontology-123", 1)
        assert file_path == "versions/ontologies/ontology-123/v1.json"

    @pytest.mark.asyncio
    async def test_get_next_version_first(self, version_history_service, mock_storage):
        """測試獲取下一個版本號（首次創建）"""
        # 模擬沒有現有版本
        mock_storage.s3_client.get_paginator.return_value.paginate.return_value = []

        version = await version_history_service._get_next_version("ontologies", "ontology-123")

        assert version == 1

    @pytest.mark.asyncio
    async def test_get_next_version_existing(self, version_history_service, mock_storage):
        """測試獲取下一個版本號（已有版本）"""
        # 模擬已有版本文件
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": "versions/ontologies/ontology-123/v1.json"},
            {"Key": "versions/ontologies/ontology-123/v2.json"},
            {"Key": "versions/ontologies/ontology-123/v5.json"},
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        version = await version_history_service._get_next_version("ontologies", "ontology-123")

        assert version == 6  # 最大版本號是 5，下一個是 6

    @pytest.mark.asyncio
    async def test_create_version(self, version_history_service, mock_storage):
        """測試創建版本記錄"""
        # 模擬沒有現有版本
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator
        mock_storage.s3_client.put_object.return_value = {}

        version_data = VersionHistoryCreate(
            resource_type="ontologies",
            resource_id="ontology-123",
            change_type="update",
            changed_by="user-123",
            change_summary="Updated ontology",
            previous_version={"name": "old"},
            current_version={"name": "new"},
        )

        version = await version_history_service.create_version(version_data)

        assert version == 1
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "bucket-version-history"
        assert call_args[1]["Key"] == "versions/ontologies/ontology-123/v1.json"

        # 驗證內容
        content = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert content["resource_type"] == "ontologies"
        assert content["resource_id"] == "ontology-123"
        assert content["version"] == 1
        assert content["change_type"] == "update"
        assert content["changed_by"] == "user-123"

    @pytest.mark.asyncio
    async def test_get_version_history(self, version_history_service, mock_storage):
        """測試獲取版本歷史列表"""
        # 模擬版本文件列表
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": "versions/ontologies/ontology-123/v1.json"},
            {"Key": "versions/ontologies/ontology-123/v2.json"},
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        # 模擬讀取版本文件內容
        version_data_1 = {
            "resource_type": "ontologies",
            "resource_id": "ontology-123",
            "version": 1,
            "change_type": "create",
            "changed_by": "user-123",
            "change_summary": "Created ontology",
            "previous_version": {},
            "current_version": {"name": "ontology"},
            "created_at": "2025-01-27T10:00:00Z",
        }
        version_data_2 = {
            "resource_type": "ontologies",
            "resource_id": "ontology-123",
            "version": 2,
            "change_type": "update",
            "changed_by": "user-123",
            "change_summary": "Updated ontology",
            "previous_version": {"name": "ontology"},
            "current_version": {"name": "updated-ontology"},
            "created_at": "2025-01-27T11:00:00Z",
        }

        def mock_get_object(Bucket, Key):
            if Key.endswith("v1.json"):
                return {"Body": Mock(read=lambda: json.dumps(version_data_1).encode("utf-8"))}
            elif Key.endswith("v2.json"):
                return {"Body": Mock(read=lambda: json.dumps(version_data_2).encode("utf-8"))}
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

        mock_storage.s3_client.get_object.side_effect = mock_get_object

        versions = await version_history_service.get_version_history(
            "ontologies", "ontology-123", limit=10
        )

        assert len(versions) == 2
        assert versions[0].version == 2  # 按版本號降序排列
        assert versions[1].version == 1
        assert versions[0].change_type == "update"
        assert versions[1].change_type == "create"

    @pytest.mark.asyncio
    async def test_get_version_history_empty(self, version_history_service, mock_storage):
        """測試獲取版本歷史列表（無版本）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        versions = await version_history_service.get_version_history(
            "ontologies", "ontology-123", limit=10
        )

        assert len(versions) == 0

    @pytest.mark.asyncio
    async def test_get_version(self, version_history_service, mock_storage):
        """測試獲取特定版本"""
        version_data = {
            "resource_type": "ontologies",
            "resource_id": "ontology-123",
            "version": 1,
            "change_type": "create",
            "changed_by": "user-123",
            "change_summary": "Created ontology",
            "previous_version": {},
            "current_version": {"name": "ontology"},
            "created_at": "2025-01-27T10:00:00Z",
        }

        mock_storage.s3_client.get_object.return_value = {
            "Body": Mock(read=lambda: json.dumps(version_data).encode("utf-8"))
        }

        version = await version_history_service.get_version("ontologies", "ontology-123", 1)

        assert version is not None
        assert version.version == 1
        assert version.resource_type == "ontologies"
        assert version.resource_id == "ontology-123"
        assert version.change_type == "create"

    @pytest.mark.asyncio
    async def test_get_version_not_exists(self, version_history_service, mock_storage):
        """測試獲取特定版本（不存在）"""
        mock_storage.s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey"}}, "GetObject"
        )

        version = await version_history_service.get_version("ontologies", "ontology-123", 999)

        assert version is None

    @pytest.mark.asyncio
    async def test_get_version_history_limit(self, version_history_service, mock_storage):
        """測試獲取版本歷史列表（限制數量）"""
        # 模擬多個版本文件
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": f"versions/ontologies/ontology-123/v{i}.json"} for i in range(1, 11)
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        # 模擬讀取版本文件內容
        def mock_get_object(Bucket, Key):
            version_num = int(Key.split("/")[-1][1:-5])  # 從 v{num}.json 提取版本號
            version_data = {
                "resource_type": "ontologies",
                "resource_id": "ontology-123",
                "version": version_num,
                "change_type": "update",
                "changed_by": "user-123",
                "change_summary": f"Updated to version {version_num}",
                "previous_version": {},
                "current_version": {"version": version_num},
                "created_at": "2025-01-27T10:00:00Z",
            }
            return {"Body": Mock(read=lambda: json.dumps(version_data).encode("utf-8"))}

        mock_storage.s3_client.get_object.side_effect = mock_get_object

        versions = await version_history_service.get_version_history(
            "ontologies", "ontology-123", limit=5
        )

        assert len(versions) == 5
        assert versions[0].version == 10  # 按版本號降序排列
        assert versions[4].version == 6
