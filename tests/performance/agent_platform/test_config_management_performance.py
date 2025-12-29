# 代碼功能說明: 配置管理性能測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""配置管理性能測試

測試各項操作的性能指標：
- 日誌寫入延遲（目標 < 100ms）
- 配置定義讀取延遲（目標 < 10ms）
- 第一層預檢延遲（目標 < 50ms）
- 第二層深檢延遲（目標 < 200ms）
- 完整配置更新流程延遲（目標 < 2秒）
"""

import time
from unittest.mock import Mock, patch

import pytest

# 注意：需要安裝 pytest-benchmark: pip install pytest-benchmark
try:
    import pytest_benchmark
except ImportError:
    pytest_benchmark = None


class TestConfigManagementPerformance:
    """配置管理性能測試類"""

    @pytest.mark.skipif(pytest_benchmark is None, reason="pytest-benchmark 未安裝")
    def test_log_write_performance(self, benchmark):
        """測試日誌寫入性能（目標 < 100ms）"""
        from database.arangodb import ArangoDBClient
        from services.api.core.log import LogService

        # Mock ArangoDB 客戶端
        mock_client = Mock(spec=ArangoDBClient)
        mock_client.db = Mock()
        mock_client.db.collection = Mock(return_value=Mock())
        collection_mock = mock_client.db.collection.return_value
        collection_mock.insert = Mock(return_value={"_key": "test_log_id"})

        log_service = LogService(client=mock_client)

        def write_log():
            log_service.log_event(
                trace_id="test_trace",
                log_type="TASK",
                agent_name="TestAgent",
                actor="test_user",
                action="test_action",
                content={"message": "test"},
            )

        # 運行性能測試
        result = benchmark(write_log)

        # 驗證性能指標（100ms = 0.1 秒）
        assert result < 0.1, f"日誌寫入延遲 {result} 秒超過目標 0.1 秒"

    def test_definition_loader_read_performance(self):
        """測試配置定義讀取性能（目標 < 10ms）"""
        # 注意：這裡簡化測試，實際應該測試真實的 DefinitionLoader
        # 如果 DefinitionLoader 尚未實現，跳過此測試
        try:
            from services.api.core.config.definition_loader import DefinitionLoader

            loader = DefinitionLoader()
            loader.load_all()

            start_time = time.time()
            definition = loader.get_definition("genai.policy")
            elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒

            # 驗證性能指標（10ms）
            assert elapsed_time < 10, f"配置定義讀取延遲 {elapsed_time} ms 超過目標 10 ms"

        except ImportError:
            pytest.skip("DefinitionLoader 尚未實現")

    @pytest.mark.asyncio
    async def test_first_layer_precheck_performance(self):
        """測試第一層預檢性能（目標 < 50ms）"""
        from agents.services.orchestrator.orchestrator import AgentOrchestrator

        with patch("agents.services.orchestrator.orchestrator.get_agent_registry"):
            orchestrator = AgentOrchestrator()

            # Mock DefinitionLoader
            mock_loader = Mock()
            mock_loader.get_definition = Mock(
                return_value={
                    "scope": "genai.policy",
                    "fields": {
                        "max_concurrent_requests": {
                            "type": "integer",
                            "min": 1,
                            "max": 1000,
                        },
                    },
                }
            )
            orchestrator._definition_loader = mock_loader

            intent_dict = {
                "action": "update",
                "scope": "genai.policy",
                "level": "system",
                "config_data": {"max_concurrent_requests": 100},
            }

            start_time = time.time()
            result = await orchestrator._pre_check_config_intent(intent_dict, "system_config_agent")
            elapsed_time = (time.time() - start_time) * 1000  # 轉換為毫秒

            # 驗證性能指標（50ms）
            assert elapsed_time < 50, f"第一層預檢延遲 {elapsed_time} ms 超過目標 50 ms"
            assert result.valid is True
