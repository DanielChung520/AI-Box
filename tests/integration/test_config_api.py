# 代碼功能說明: Config API 整合測試（WBS-5.1.2: 整合測試）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""Config API 整合測試"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestConfigAPI:
    """Config API 整合測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        from api.main import app

        return TestClient(app)

    def test_get_effective_config(self, client: TestClient):
        """測試獲取有效配置"""
        tenant_id = "test-tenant-123"
        user_id = "test-user-456"
        response = client.get(
            f"/api/v1/configs/effective?section=genai&tenant_id={tenant_id}&user_id={user_id}"
        )
        assert response.status_code == 200

    def test_get_system_config(self, client: TestClient):
        """測試獲取系統配置"""
        response = client.get("/api/v1/configs/system?section=genai")
        assert response.status_code == 200
