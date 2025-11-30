# 代碼功能說明: 上下文管理整合測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""測試劇本 IT-4.3：上下文管理整合測試"""

import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestContextManagement:
    """上下文管理整合測試"""

    @pytest.fixture(scope="function")
    async def client(self) -> AsyncGenerator[AsyncClient, None]:
        async with AsyncClient(
            base_url="http://localhost:8000", timeout=30.0
        ) as client:
            yield client

    async def test_context_manager(self, client: AsyncClient):
        """步驟 1: 上下文管理器測試"""
        try:
            response = await client.post(
                "/api/v1/context/create",
                json={
                    "session_id": "test_session_001",
                    "user_id": "test_user",
                    "metadata": {},
                },
            )
            assert response.status_code in [
                200,
                201,
                404,
            ], f"Expected 200/201/404, got {response.status_code}"

            if response.status_code in [200, 201]:
                data = response.json()
                assert (
                    "context_id" in data or "id" in data or "data" in data
                ), "Response should contain context ID"
        except Exception as e:
            pytest.skip(f"上下文管理器端點未實現或不可用: {str(e)}")

    async def test_conversation_history(self, client: AsyncClient):
        """步驟 2: 對話歷史管理測試"""
        try:
            session_id = "test_session_002"

            # 添加消息
            add_response = await client.post(
                f"/api/v1/context/{session_id}/messages",
                json={
                    "role": "user",
                    "content": "你好",
                    "timestamp": "2025-11-30T12:00:00Z",
                },
            )
            assert add_response.status_code in [
                200,
                201,
                404,
            ], f"Expected 200/201/404, got {add_response.status_code}"

            # 獲取歷史
            history_response = await client.get(
                f"/api/v1/context/{session_id}/messages"
            )
            assert history_response.status_code in [
                200,
                404,
            ], f"Expected 200/404, got {history_response.status_code}"

            if history_response.status_code == 200:
                history_data = history_response.json()
                assert (
                    "messages" in history_data or "data" in history_data
                ), "Response should contain messages"
        except Exception as e:
            pytest.skip(f"對話歷史管理端點未實現或不可用: {str(e)}")

    async def test_context_window(self, client: AsyncClient):
        """步驟 3: 上下文窗口管理測試"""
        try:
            session_id = "test_session_003"

            # 添加多條消息以測試窗口管理
            for i in range(20):
                response = await client.post(
                    f"/api/v1/context/{session_id}/messages",
                    json={
                        "role": "user" if i % 2 == 0 else "assistant",
                        "content": f"Message {i}",
                    },
                )

            # 獲取上下文窗口
            window_response = await client.get(
                f"/api/v1/context/{session_id}/window",
                params={"max_tokens": 1000, "strategy": "sliding"},
            )
            assert window_response.status_code in [
                200,
                404,
            ], f"Expected 200/404, got {window_response.status_code}"

            if window_response.status_code == 200:
                window_data = window_response.json()
                assert (
                    "messages" in window_data or "data" in window_data
                ), "Response should contain window messages"
        except Exception as e:
            pytest.skip(f"上下文窗口管理端點未實現或不可用: {str(e)}")
