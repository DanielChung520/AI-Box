# 代碼功能說明: OntologyStoreService 單元測試（WBS-5.1.1: 單元測試）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""OntologyStoreService 單元測試"""

from __future__ import annotations

from unittest.mock import Mock

from services.api.models.ontology import OntologyCreate


class TestOntologyStoreService:
    """OntologyStoreService 測試類"""

    def test_save_ontology_creates_new(self, ontology_store_service):
        """測試創建新的 Ontology"""
        ontology_create = OntologyCreate(
            type="base",
            name="test-ontology",
            version="1.0.0",
            ontology_name="Test Ontology",
            entity_classes=[],
            object_properties=[],
        )

        ontology_store_service._collection.get = Mock(return_value=None)
        ontology_store_service._collection.insert = Mock()

        result_id = ontology_store_service.save_ontology(ontology_create)

        assert result_id is not None
        ontology_store_service._collection.insert.assert_called_once()

    def test_get_ontology_with_tenant_isolation(self, ontology_store_service, sample_tenant_id):
        """測試租戶隔離"""
        ontology_id = "base-test-ontology-1.0.0"
        other_tenant_id = "other-tenant-789"

        doc = {
            "_key": ontology_id,
            "tenant_id": other_tenant_id,
            "type": "base",
            "name": "test-ontology",
        }
        ontology_store_service._collection.get = Mock(return_value=doc)

        result = ontology_store_service.get_ontology(ontology_id, tenant_id=sample_tenant_id)

        assert result is None
