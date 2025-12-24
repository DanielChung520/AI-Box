# 代碼功能說明: Pytest 配置和共用 Fixtures（WBS-5: 測試與驗證）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""Pytest 配置和共用 Fixtures"""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from database.arangodb import ArangoDBClient
from services.api.services.config_store_service import ConfigStoreService
from services.api.services.ontology_store_service import OntologyStoreService


@pytest.fixture
def mock_arangodb_client():
    """模擬 ArangoDB 客戶端"""
    client = Mock(spec=ArangoDBClient)
    client.db = Mock()
    client.db.has_collection = Mock(return_value=True)
    client.db.collection = Mock(return_value=Mock())
    client.get_or_create_collection = Mock(return_value=Mock())
    return client


@pytest.fixture
def ontology_store_service(mock_arangodb_client):
    """創建 OntologyStoreService 實例（用於測試）"""
    service = OntologyStoreService.__new__(OntologyStoreService)
    service._client = mock_arangodb_client
    service._logger = Mock()
    service._collection = Mock()
    return service


@pytest.fixture
def config_store_service(mock_arangodb_client):
    """創建 ConfigStoreService 實例（用於測試）"""
    service = ConfigStoreService.__new__(ConfigStoreService)
    service._client = mock_arangodb_client
    service._logger = Mock()
    service._system_collection = Mock()
    service._tenant_collection = Mock()
    service._user_collection = Mock()
    return service


@pytest.fixture
def sample_tenant_id():
    """示例租戶 ID"""
    return "test-tenant-123"


@pytest.fixture
def sample_user_id():
    """示例用戶 ID"""
    return "test-user-456"
