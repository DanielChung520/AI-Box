# 代碼功能說明: API 性能測試（WBS-5.2.1: API 性能測試）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""API 性能測試"""

from __future__ import annotations

import time
from statistics import median

import pytest
from fastapi.testclient import TestClient


@pytest.mark.performance
class TestAPIPerformance:
    """API 性能測試類"""

    @pytest.fixture
    def client(self):
        """創建測試客戶端"""
        from api.main import app

        return TestClient(app)

    def test_ontology_api_response_time(self, client: TestClient):
        """測試 Ontology API 回應時間 < 200ms P95"""
        times = []
        for _ in range(10):
            start = time.time()
            response = client.get("/api/v1/ontologies")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            assert response.status_code == 200

        p95_time = median(sorted(times)[int(len(times) * 0.95) :])
        assert p95_time < 200, f"P95 回應時間 {p95_time}ms 超過 200ms"
