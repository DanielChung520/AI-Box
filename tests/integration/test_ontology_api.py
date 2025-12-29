# 代碼功能說明: Ontology API 整合測試（WBS-5.1.2: 整合測試）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""Ontology API 整合測試"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestOntologyAPI:
    """Ontology API 整合測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        from api.main import app

        return TestClient(app)

    def test_create_ontology(self, client: TestClient):
        """測試創建 Ontology"""
        ontology_data = {
            "type": "base",
            "name": "test-ontology",
            "version": "1.0.0",
            "ontology_name": "Test Ontology",
            "entity_classes": [],
            "object_properties": [],
        }

        response = client.post("/api/v1/ontologies", json=ontology_data)
        assert response.status_code in [200, 201]

    def test_get_ontology(self, client: TestClient):
        """測試獲取 Ontology"""
        ontology_id = "base-test-ontology-1.0.0"
        response = client.get(f"/api/v1/ontologies/{ontology_id}")
        assert response.status_code in [200, 404]  # 可能不存在

    def test_merge_ontologies(self, client: TestClient):
        """測試合併 Ontology"""
        merge_request = {
            "domain_files": ["domain-enterprise"],
            "major_file": "major-manufacture",
        }
        response = client.post("/api/v1/ontologies/merge/query", json=merge_request)
        assert response.status_code == 200
