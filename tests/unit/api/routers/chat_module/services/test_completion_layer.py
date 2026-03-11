# 代碼功能說明: CompletionLayer 單元測試
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

"""CompletionLayer.complete 單元測試。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from api.routers.chat_module.services.completion_layer import (
    CompletionLayer,
    FinalResponse,
)


class TestCompletionLayerComplete:
    """CompletionLayer.complete 測試。"""

    @pytest.mark.asyncio
    async def test_complete_success_response(self) -> None:
        """action_result 包含 content，status='success'。"""
        layer = CompletionLayer()
        action_result = {"content": "回覆內容"}

        resp: FinalResponse = await layer.complete(action_result=action_result)

        assert resp.content == "回覆內容"
        assert resp.status == "success"

    @pytest.mark.asyncio
    async def test_complete_error_response(self) -> None:
        """action_result 包含 error 鍵，status='error'，content 含 '抱歉'。"""
        layer = CompletionLayer()
        action_result = {"error": "timeout", "content": ""}

        resp: FinalResponse = await layer.complete(action_result=action_result)

        assert resp.status == "error"
        assert "抱歉" in resp.content

    @pytest.mark.asyncio
    async def test_complete_with_metadata(self) -> None:
        """傳入 perception_result 和 intent_result，metadata 中應包含對應資訊。"""
        layer = CompletionLayer()
        action_result = {"content": "ok"}
        perception_result = SimpleNamespace(
            perception_metadata={"corrections": [], "errors": []},
        )
        intent_result = SimpleNamespace(
            intent_name="BUSINESS_QUERY",
            confidence=0.95,
        )

        resp: FinalResponse = await layer.complete(
            action_result=action_result,
            perception_result=perception_result,
            intent_result=intent_result,
        )

        assert resp.status == "success"
        assert "perception" in resp.metadata
        assert resp.metadata["perception"] == {"corrections": [], "errors": []}
        assert "intent" in resp.metadata
        assert resp.metadata["intent"]["name"] == "BUSINESS_QUERY"
        assert resp.metadata["intent"]["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_complete_none_action_result(self) -> None:
        """action_result=None，status='error'。"""
        layer = CompletionLayer()

        resp: FinalResponse = await layer.complete(action_result=None)

        assert resp.status == "error"
        assert "抱歉" in resp.content
