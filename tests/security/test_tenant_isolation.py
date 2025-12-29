# 代碼功能說明: 租戶隔離安全測試（WBS-5.3.1: 租戶隔離測試）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""租戶隔離安全測試"""

from __future__ import annotations

from unittest.mock import Mock

import pytest


@pytest.mark.security
class TestTenantIsolation:
    """租戶隔離測試類"""

    def test_tenant_cannot_access_other_tenant_ontology(self, ontology_store_service):
        """測試租戶無法存取其他租戶的 Ontology"""
        tenant_id_1 = "tenant-1"
        tenant_id_2 = "tenant-2"
        ontology_id = "base-test-1.0.0"

        doc = {
            "_key": ontology_id,
            "tenant_id": tenant_id_2,
            "type": "base",
            "name": "test",
        }
        ontology_store_service._collection.get = Mock(return_value=doc)

        result = ontology_store_service.get_ontology(ontology_id, tenant_id=tenant_id_1)
        assert result is None
