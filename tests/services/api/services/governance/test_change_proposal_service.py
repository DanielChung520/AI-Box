# 代碼功能說明: SeaweedFS 變更提案服務單元測試
# 創建日期: 2025-12-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""SeaweedFS 變更提案服務單元測試 - 測試變更提案服務"""

import json
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from services.api.models.change_proposal import ChangeProposalCreate, ProposalStatus
from services.api.services.governance.change_proposal_service import SeaweedFSChangeProposalService
from storage.s3_storage import S3FileStorage


class TestSeaweedFSChangeProposalService:
    """SeaweedFSChangeProposalService 測試類"""

    @pytest.fixture
    def mock_storage(self):
        """創建模擬 S3FileStorage"""
        storage = MagicMock(spec=S3FileStorage)
        storage.s3_client = MagicMock()
        storage.bucket = "bucket-change-proposals"
        return storage

    @pytest.fixture
    def change_proposal_service(self, mock_storage):
        """創建 SeaweedFSChangeProposalService 實例"""
        mock_storage.s3_client.head_bucket.return_value = None
        return SeaweedFSChangeProposalService(storage=mock_storage)

    def test_get_proposal_file_path_with_resource_id(self, change_proposal_service):
        """測試提案文件路徑生成（帶 resource_id）"""
        file_path = change_proposal_service._get_proposal_file_path(
            "config_update", "config-123", "proposal-456"
        )
        assert file_path == "proposals/config_update/config-123/proposal-456.json"

    def test_get_proposal_file_path_without_resource_id(self, change_proposal_service):
        """測試提案文件路徑生成（無 resource_id）"""
        file_path = change_proposal_service._get_proposal_file_path(
            "config_update", None, "proposal-456"
        )
        assert file_path == "proposals/config_update/global/proposal-456.json"

    @pytest.mark.asyncio
    async def test_create_proposal(self, change_proposal_service, mock_storage):
        """測試創建變更提案"""
        mock_storage.s3_client.put_object.return_value = {}

        proposal_data = ChangeProposalCreate(
            proposal_type="config_update",
            resource_id="config-123",
            proposed_by="user-123",
            proposal_data={"key": "value"},
            approval_required=True,
        )

        proposal_id = await change_proposal_service.create_proposal(proposal_data)

        assert proposal_id is not None
        assert "config_update" in proposal_id
        assert "config-123" in proposal_id
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        assert call_args[1]["Bucket"] == "bucket-change-proposals"
        assert call_args[1]["Key"].startswith("proposals/config_update/config-123/")

        # 驗證內容
        content = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert content["proposal_type"] == "config_update"
        assert content["resource_id"] == "config-123"
        assert content["proposed_by"] == "user-123"
        assert content["status"] == ProposalStatus.PENDING.value
        assert content["approval_required"] is True

    @pytest.mark.asyncio
    async def test_create_proposal_global(self, change_proposal_service, mock_storage):
        """測試創建變更提案（全局提案，無 resource_id）"""
        mock_storage.s3_client.put_object.return_value = {}

        proposal_data = ChangeProposalCreate(
            proposal_type="system_config_update",
            resource_id=None,
            proposed_by="user-123",
            proposal_data={"key": "value"},
            approval_required=False,
        )

        proposal_id = await change_proposal_service.create_proposal(proposal_data)

        assert proposal_id is not None
        call_args = mock_storage.s3_client.put_object.call_args
        assert "proposals/system_config_update/global/" in call_args[1]["Key"]

    @pytest.mark.asyncio
    async def test_get_proposal(self, change_proposal_service, mock_storage):
        """測試獲取提案詳情"""
        proposal_data = {
            "proposal_id": "proposal-123",
            "proposal_type": "config_update",
            "resource_id": "config-123",
            "proposed_by": "user-123",
            "status": ProposalStatus.PENDING.value,
            "proposal_data": {"key": "value"},
            "approval_required": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z",
        }

        # 模擬搜索提案文件
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [{"Key": "proposals/config_update/config-123/proposal-123.json"}]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_storage.s3_client.get_object.return_value = {
            "Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))
        }

        proposal = await change_proposal_service.get_proposal("proposal-123")

        assert proposal is not None
        assert proposal.proposal_id == "proposal-123"
        assert proposal.proposal_type == "config_update"
        assert proposal.status == ProposalStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_proposal_not_exists(self, change_proposal_service, mock_storage):
        """測試獲取提案詳情（不存在）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        proposal = await change_proposal_service.get_proposal("non-existent-proposal")

        assert proposal is None

    @pytest.mark.asyncio
    async def test_approve_proposal(self, change_proposal_service, mock_storage):
        """測試審批提案"""
        proposal_data = {
            "proposal_id": "proposal-123",
            "proposal_type": "config_update",
            "resource_id": "config-123",
            "proposed_by": "user-123",
            "status": ProposalStatus.PENDING.value,
            "proposal_data": {"key": "value"},
            "approval_required": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z",
        }

        # 模擬搜索提案文件
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [{"Key": "proposals/config_update/config-123/proposal-123.json"}]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_storage.s3_client.get_object.return_value = {
            "Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))
        }
        mock_storage.s3_client.put_object.return_value = {}

        # 模擬 _apply_proposal_to_arangodb 方法
        change_proposal_service._apply_proposal_to_arangodb = AsyncMock()

        result = await change_proposal_service.approve_proposal("proposal-123", "admin-123")

        assert result is True
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        content = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert content["status"] == ProposalStatus.APPROVED.value
        assert content["approved_by"] == "admin-123"
        assert "approved_at" in content

        # 驗證應用到 ArangoDB 的方法被調用
        change_proposal_service._apply_proposal_to_arangodb.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_proposal_not_exists(self, change_proposal_service, mock_storage):
        """測試審批提案（不存在）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        result = await change_proposal_service.approve_proposal(
            "non-existent-proposal", "admin-123"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_reject_proposal(self, change_proposal_service, mock_storage):
        """測試拒絕提案"""
        proposal_data = {
            "proposal_id": "proposal-123",
            "proposal_type": "config_update",
            "resource_id": "config-123",
            "proposed_by": "user-123",
            "status": ProposalStatus.PENDING.value,
            "proposal_data": {"key": "value"},
            "approval_required": True,
            "created_at": "2025-01-27T10:00:00Z",
            "updated_at": "2025-01-27T10:00:00Z",
        }

        # 模擬搜索提案文件
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [{"Key": "proposals/config_update/config-123/proposal-123.json"}]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        mock_storage.s3_client.get_object.return_value = {
            "Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))
        }
        mock_storage.s3_client.put_object.return_value = {}

        result = await change_proposal_service.reject_proposal(
            "proposal-123", "admin-123", "不符合規範"
        )

        assert result is True
        mock_storage.s3_client.put_object.assert_called_once()
        call_args = mock_storage.s3_client.put_object.call_args
        content = json.loads(call_args[1]["Body"].decode("utf-8"))
        assert content["status"] == ProposalStatus.REJECTED.value
        assert content["rejected_by"] == "admin-123"
        assert content["rejection_reason"] == "不符合規範"
        assert "rejected_at" in content

    @pytest.mark.asyncio
    async def test_reject_proposal_not_exists(self, change_proposal_service, mock_storage):
        """測試拒絕提案（不存在）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        result = await change_proposal_service.reject_proposal(
            "non-existent-proposal", "admin-123", "reason"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_list_proposals(self, change_proposal_service, mock_storage):
        """測試列出提案列表"""
        # 模擬提案文件列表
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": "proposals/config_update/config-123/proposal-1.json"},
            {"Key": "proposals/config_update/config-123/proposal-2.json"},
            {"Key": "proposals/ontology_update/ontology-456/proposal-3.json"},
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        # 模擬讀取提案文件內容
        def mock_get_object(Bucket, Key):
            proposal_num = Key.split("/")[-1].split(".")[0].split("-")[-1]
            proposal_data = {
                "proposal_id": f"proposal-{proposal_num}",
                "proposal_type": "config_update" if "config" in Key else "ontology_update",
                "resource_id": "config-123" if "config" in Key else "ontology-456",
                "proposed_by": "user-123",
                "status": (
                    ProposalStatus.PENDING.value
                    if proposal_num == "1"
                    else ProposalStatus.APPROVED.value
                ),
                "proposal_data": {"key": "value"},
                "approval_required": True,
                "created_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
                "updated_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
            }
            return {"Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))}

        mock_storage.s3_client.get_object.side_effect = mock_get_object

        proposals = await change_proposal_service.list_proposals(limit=10)

        assert len(proposals) == 3
        # 按創建時間降序排列
        assert proposals[0].proposal_id == "proposal-3"

    @pytest.mark.asyncio
    async def test_list_proposals_with_filters(self, change_proposal_service, mock_storage):
        """測試列出提案列表（帶過濾條件）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": "proposals/config_update/config-123/proposal-1.json"},
            {"Key": "proposals/config_update/config-123/proposal-2.json"},
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        def mock_get_object(Bucket, Key):
            proposal_num = Key.split("/")[-1].split(".")[0].split("-")[-1]
            proposal_data = {
                "proposal_id": f"proposal-{proposal_num}",
                "proposal_type": "config_update",
                "resource_id": "config-123",
                "proposed_by": "user-123",
                "status": (
                    ProposalStatus.PENDING.value
                    if proposal_num == "1"
                    else ProposalStatus.APPROVED.value
                ),
                "proposal_data": {"key": "value"},
                "approval_required": True,
                "created_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
                "updated_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
            }
            return {"Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))}

        mock_storage.s3_client.get_object.side_effect = mock_get_object

        # 測試按提案類型過濾
        proposals = await change_proposal_service.list_proposals(
            proposal_type="config_update", limit=10
        )
        assert len(proposals) == 2

        # 測試按資源ID過濾
        proposals = await change_proposal_service.list_proposals(
            proposal_type="config_update", resource_id="config-123", limit=10
        )
        assert len(proposals) == 2

        # 測試按狀態過濾
        proposals = await change_proposal_service.list_proposals(
            proposal_type="config_update", status=ProposalStatus.PENDING, limit=10
        )
        assert len(proposals) == 1
        assert proposals[0].status == ProposalStatus.PENDING

    @pytest.mark.asyncio
    async def test_list_proposals_empty(self, change_proposal_service, mock_storage):
        """測試列出提案列表（無提案）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=False)
        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        proposals = await change_proposal_service.list_proposals(limit=10)

        assert len(proposals) == 0

    @pytest.mark.asyncio
    async def test_list_proposals_limit(self, change_proposal_service, mock_storage):
        """測試列出提案列表（限制數量）"""
        mock_page = MagicMock()
        mock_page.__iter__ = Mock(return_value=iter([mock_page]))
        mock_page.__contains__ = Mock(return_value=True)
        mock_page["Contents"] = [
            {"Key": f"proposals/config_update/config-123/proposal-{i}.json"} for i in range(1, 11)
        ]

        mock_paginator = MagicMock()
        mock_paginator.paginate.return_value = [mock_page]
        mock_storage.s3_client.get_paginator.return_value = mock_paginator

        def mock_get_object(Bucket, Key):
            proposal_num = Key.split("/")[-1].split(".")[0].split("-")[-1]
            proposal_data = {
                "proposal_id": f"proposal-{proposal_num}",
                "proposal_type": "config_update",
                "resource_id": "config-123",
                "proposed_by": "user-123",
                "status": ProposalStatus.PENDING.value,
                "proposal_data": {"key": "value"},
                "approval_required": True,
                "created_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
                "updated_at": f"2025-01-27T{10 + int(proposal_num)}:00:00Z",
            }
            return {"Body": Mock(read=lambda: json.dumps(proposal_data).encode("utf-8"))}

        mock_storage.s3_client.get_object.side_effect = mock_get_object

        proposals = await change_proposal_service.list_proposals(limit=5)

        assert len(proposals) == 5
