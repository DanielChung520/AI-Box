# 代碼功能說明: Router LLM v4.0 單元測試（L1 語義理解層）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Router LLM v4.0 單元測試 - 測試 L1 語義理解層輸出"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from agents.task_analyzer.models import RouterInput, SemanticUnderstandingOutput
from agents.task_analyzer.router_llm import RouterLLM, SAFE_FALLBACK_SEMANTIC


class TestRouterLLMV4:
    """Router LLM v4.0 測試類"""

    @pytest.fixture
    def router_llm(self):
        """創建 RouterLLM 實例"""
        return RouterLLM()

    @pytest.fixture
    def router_input(self):
        """創建 RouterInput 實例"""
        return RouterInput(
            user_query="幫我產生Data Agent文件",
            session_context={},
            system_constraints={},
        )

    @pytest.mark.asyncio
    async def test_route_v4_basic_semantic_understanding(self, router_llm, router_input):
        """測試基本語義理解輸出"""
        # Mock LLM 響應
        mock_response = {
            "content": json.dumps(
                {
                    "topics": ["document", "agent_design"],
                    "entities": ["Data Agent"],
                    "action_signals": ["generate", "create", "design"],
                    "modality": "instruction",
                    "certainty": 0.95,
                }
            )
        }

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 驗證結果類型
            assert isinstance(result, SemanticUnderstandingOutput)

            # 驗證字段完整性
            assert result.topics == ["document", "agent_design"]
            assert result.entities == ["Data Agent"]
            assert result.action_signals == ["generate", "create", "design"]
            assert result.modality == "instruction"
            assert result.certainty == 0.95

    @pytest.mark.asyncio
    async def test_route_v4_schema_validation(self, router_llm, router_input):
        """測試 Schema 驗證"""
        # 測試缺少必要字段的情況
        mock_response = {
            "content": json.dumps(
                {
                    "topics": ["document"],
                    # 缺少 entities, action_signals, modality, certainty
                }
            )
        }

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback
            assert result == SAFE_FALLBACK_SEMANTIC

    @pytest.mark.asyncio
    async def test_route_v4_certainty_threshold(self, router_llm, router_input):
        """測試確定性分數門檻檢查"""
        # 測試 certainty < 0.6 的情況
        mock_response = {
            "content": json.dumps(
                {
                    "topics": ["document"],
                    "entities": ["Data Agent"],
                    "action_signals": ["generate"],
                    "modality": "instruction",
                    "certainty": 0.5,  # 低於門檻 0.6
                }
            )
        }

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback
            assert result == SAFE_FALLBACK_SEMANTIC

    @pytest.mark.asyncio
    async def test_route_v4_certainty_range(self, router_llm, router_input):
        """測試確定性分數範圍驗證"""
        # 測試 certainty > 1.0 的情況（應該被 Pydantic 驗證拒絕）
        mock_response = {
            "content": json.dumps(
                {
                    "topics": ["document"],
                    "entities": ["Data Agent"],
                    "action_signals": ["generate"],
                    "modality": "instruction",
                    "certainty": 1.5,  # 超出範圍
                }
            )
        }

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback（因為 Schema 驗證失敗）
            assert result == SAFE_FALLBACK_SEMANTIC

    @pytest.mark.asyncio
    async def test_route_v4_modality_values(self, router_llm):
        """測試 modality 值的驗證"""
        modalities = ["instruction", "question", "conversation", "command"]

        for modality in modalities:
            router_input = RouterInput(
                user_query=f"測試 {modality}",
                session_context={},
                system_constraints={},
            )

            mock_response = {
                "content": json.dumps(
                    {
                        "topics": ["test"],
                        "entities": [],
                        "action_signals": ["test"],
                        "modality": modality,
                        "certainty": 0.9,
                    }
                )
            }

            with patch.object(router_llm, "_get_llm_client") as mock_get_client:
                mock_client = MagicMock()
                mock_client.chat = AsyncMock(return_value=mock_response)
                mock_get_client.return_value = mock_client

                result = await router_llm.route_v4(router_input)

                # 驗證 modality 值正確
                assert result.modality == modality
                assert isinstance(result, SemanticUnderstandingOutput)

    @pytest.mark.asyncio
    async def test_route_v4_empty_response(self, router_llm, router_input):
        """測試空響應處理"""
        mock_response = {"content": ""}

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback
            assert result == SAFE_FALLBACK_SEMANTIC

    @pytest.mark.asyncio
    async def test_route_v4_invalid_json(self, router_llm, router_input):
        """測試無效 JSON 處理"""
        mock_response = {"content": "這不是有效的 JSON"}

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback
            assert result == SAFE_FALLBACK_SEMANTIC

    @pytest.mark.asyncio
    async def test_route_v4_no_intent_in_output(self, router_llm, router_input):
        """測試輸出中不包含 intent 相關字段（L1 層級不應該產生 intent）"""
        mock_response = {
            "content": json.dumps(
                {
                    "topics": ["document"],
                    "entities": ["Data Agent"],
                    "action_signals": ["generate"],
                    "modality": "instruction",
                    "certainty": 0.9,
                    # 注意：不應該包含 intent_type, needs_agent, needs_tools 等字段
                }
            )
        }

        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.chat = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await router_llm.route_v4(router_input)

            # 驗證結果是 SemanticUnderstandingOutput，不包含 intent 相關字段
            assert isinstance(result, SemanticUnderstandingOutput)
            assert not hasattr(result, "intent_type")
            assert not hasattr(result, "needs_agent")
            assert not hasattr(result, "needs_tools")
            assert not hasattr(result, "complexity")
            assert not hasattr(result, "risk_level")

    @pytest.mark.asyncio
    async def test_route_v4_exception_handling(self, router_llm, router_input):
        """測試異常處理"""
        with patch.object(router_llm, "_get_llm_client") as mock_get_client:
            mock_get_client.side_effect = Exception("LLM client error")

            result = await router_llm.route_v4(router_input)

            # 應該返回 fallback
            assert result == SAFE_FALLBACK_SEMANTIC


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
