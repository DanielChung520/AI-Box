# 代碼功能說明: 合規檢查 API 測試（WBS-5.4: 合規驗證）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""合規檢查 API 測試"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.compliance
class TestComplianceAPI:
    """合規檢查 API 測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        from api.main import app

        return TestClient(app)

    def test_check_all_compliance(self, client: TestClient):
        """測試檢查所有合規標準"""
        response = client.get("/api/v1/compliance/check")
        assert response.status_code == 200
        data = response.json()
        assert "report_id" in data
        assert "standards" in data
        assert "results" in data

    def test_check_iso_42001_compliance(self, client: TestClient):
        """測試 ISO/IEC 42001 合規檢查"""
        response = client.get("/api/v1/compliance/check/iso_42001")
        assert response.status_code == 200
