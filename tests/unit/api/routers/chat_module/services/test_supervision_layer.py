# 代碼功能說明: SupervisionLayer 單元測試
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

"""SupervisionLayer.supervise 單元測試。"""

from __future__ import annotations

import asyncio

import pytest

from api.routers.chat_module.services.supervision_layer import (
    SupervisionConfig,
    SupervisionLayer,
    SupervisionResult,
)


class TestSupervisionLayerSupervise:
    """SupervisionLayer.supervise 測試。"""

    @pytest.mark.asyncio
    async def test_supervise_success(self) -> None:
        """協程成功完成，success=True, retries_used=0。"""
        layer = SupervisionLayer()

        async def _ok() -> dict[str, str]:
            return {"content": "ok"}

        result: SupervisionResult = await layer.supervise(action_coro=_ok())

        assert result.success is True
        assert result.result == {"content": "ok"}
        assert result.retries_used == 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_supervise_timeout(self) -> None:
        """協程超時，success=False, error 包含 '超時'。"""
        layer = SupervisionLayer()

        async def _slow() -> str:
            await asyncio.sleep(10)
            return "done"

        config = SupervisionConfig(timeout_seconds=0.05, max_retries=0)
        result: SupervisionResult = await layer.supervise(
            action_coro=_slow(),
            config=config,
        )

        assert result.success is False
        assert result.error is not None
        assert "超時" in result.error

    @pytest.mark.asyncio
    async def test_supervise_retry_on_failure(self) -> None:
        """第一次失敗、第二次成功（經由 action_factory），retries_used=1。"""
        layer = SupervisionLayer()

        call_count = 0

        async def _failing() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("first attempt fails")
            return "retry ok"

        config = SupervisionConfig(max_retries=1, retry_delay_seconds=0.01)
        result: SupervisionResult = await layer.supervise(
            action_coro=_failing(),
            config=config,
            action_factory=_failing,
        )

        assert result.success is True
        assert result.result == "retry ok"
        assert result.retries_used == 1

    @pytest.mark.asyncio
    async def test_supervise_max_retries_exceeded(self) -> None:
        """action_factory 始終失敗，超過 max_retries，success=False。"""
        layer = SupervisionLayer()

        async def _always_fail() -> str:
            raise RuntimeError("always fails")

        config = SupervisionConfig(max_retries=1, retry_delay_seconds=0.01)
        result: SupervisionResult = await layer.supervise(
            action_coro=_always_fail(),
            config=config,
            action_factory=_always_fail,
        )

        assert result.success is False
        assert result.retries_used == 1
        assert result.error is not None
