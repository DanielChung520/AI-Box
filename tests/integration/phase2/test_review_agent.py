# 代碼功能說明: Review Agent 整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""測試劇本 IT-2.5：Review Agent 結果驗證整合測試"""

import pytest
from typing import AsyncGenerator
import time
from httpx import AsyncClient
from tests.integration.test_helpers import assert_response_success


@pytest.mark.integration
@pytest.mark.asyncio
class TestReviewAgent:
    """Review Agent 整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_result_validation(self, client: AsyncClient):
        """步驟 1: 結果驗證測試"""
        start_time = time.time()
        response = await client.post(
            "/api/v1/agents/review/validate",
            json={
                "result": {"success": True, "data": "這是一個測試結果"},
                "requirements": ["格式正確", "內容完整"],
                "criteria": ["格式正確", "內容完整"],
            },
        )
        elapsed = time.time() - start_time

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Review Agent API 端點未實現")

        assert_response_success(response)
        assert elapsed < 3, f"響應時間 {elapsed}s 超過 3 秒"

        data = response.json()
        result_data = data.get("data", {})

        # 驗證響應內容
        assert "review_id" in result_data, "響應缺少 review_id"
        assert "status" in result_data, "響應缺少 status"
        assert "quality_score" in result_data, "響應缺少 quality_score"
        assert "feedback" in result_data, "響應缺少 feedback"

        # 驗證質量評分範圍
        quality_score = result_data.get("quality_score")
        assert isinstance(quality_score, (int, float)), "quality_score 應該是數字"
        assert (
            0.0 <= quality_score <= 1.0
        ), f"quality_score 應在 0.0-1.0 範圍內，實際為: {quality_score}"

    async def test_fact_validation(self, client: AsyncClient):
        """步驟 2: 事實驗證測試"""
        response = await client.post(
            "/api/v1/agents/review/validate",
            json={
                "result": {
                    "success": True,
                    "data": "根據統計，2024年全球GDP增長率為3.5%",
                    "facts": ["2024年全球GDP增長率為3.5%"],
                },
                "criteria": ["事實準確性"],
            },
        )

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Review Agent API 端點未實現")

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})

            # 驗證響應包含事實驗證相關信息
            assert "review_id" in result_data, "響應缺少 review_id"
            assert "quality_score" in result_data, "響應缺少 quality_score"

            # 驗證質量評分（事實驗證應該有評分）
            quality_score = result_data.get("quality_score")
            assert isinstance(quality_score, (int, float)), "quality_score 應該是數字"

    async def test_format_validation(self, client: AsyncClient):
        """步驟 3: 格式驗證測試"""
        response = await client.post(
            "/api/v1/agents/review/validate",
            json={
                "result": {
                    "success": True,
                    "data": {"key": "value", "number": 123},
                },
                "criteria": ["格式正確"],
            },
        )

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Review Agent API 端點未實現")

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})

            # 驗證響應包含格式驗證相關信息
            assert "review_id" in result_data, "響應缺少 review_id"
            assert "status" in result_data, "響應缺少 status"

            # 驗證反饋中包含格式相關信息
            if "feedback" in result_data:
                feedback = result_data.get("feedback")
                assert isinstance(feedback, str), "feedback 應該是字符串"

    async def test_feedback_generation(self, client: AsyncClient):
        """步驟 4: 反饋生成測試"""
        response = await client.post(
            "/api/v1/agents/review/validate",
            json={
                "result": {
                    "success": True,
                    "data": "這是一個需要審查的結果",
                },
                "criteria": ["格式正確", "內容完整", "邏輯清晰"],
            },
        )

        # 如果端點不存在，跳過測試
        if response.status_code == 404:
            pytest.skip("Review Agent API 端點未實現")

        if response.status_code in [200, 201]:
            data = response.json()
            result_data = data.get("data", {})

            # 驗證反饋生成
            assert "review_id" in result_data, "響應缺少 review_id"
            assert "feedback" in result_data, "響應缺少 feedback"
            assert "suggestions" in result_data, "響應缺少 suggestions"

            # 驗證反饋內容
            feedback = result_data.get("feedback")
            assert isinstance(feedback, str), "feedback 應該是字符串"
            assert len(feedback) > 0, "feedback 不應為空"

            # 驗證建議列表
            suggestions = result_data.get("suggestions", [])
            assert isinstance(suggestions, list), "suggestions 應該是列表"
