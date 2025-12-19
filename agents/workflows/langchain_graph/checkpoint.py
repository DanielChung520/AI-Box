# 代碼功能說明: LangChain/Graph checkpoint 與狀態儲存
# 創建日期: 2025-11-26 20:07 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 20:07 (UTC+8)

"""提供 LangGraph checkpoint builder 與 Redis 儲存實作。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Iterator, Sequence

import redis  # type: ignore[import-untyped]
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.memory import MemorySaver

from agents.workflows.settings import LangChainGraphSettings

logger = logging.getLogger(__name__)


def _config_thread_id(config: RunnableConfig) -> str:
    configurable = config.get("configurable") or {}
    return (
        configurable.get("thread_id")
        or configurable.get("task_id")
        or configurable.get("config_id")
        or "default"
    )


def _config_checkpoint_id(config: RunnableConfig) -> str:
    configurable = config.get("configurable") or {}
    return (
        configurable.get("checkpoint_id")
        or configurable.get("langgraph_checkpoint_id")
        or _config_thread_id(config)
    )


class RedisCheckpointSaver(BaseCheckpointSaver[int]):
    """最小可行的 Redis checkpoint saver。"""

    def __init__(
        self,
        *,
        redis_url: str,
        namespace: str,
        ttl_seconds: int,
    ) -> None:
        super().__init__()
        self._redis = redis.Redis.from_url(redis_url)
        self._namespace = namespace
        self._ttl = ttl_seconds

    def _key(self, config: RunnableConfig) -> str:
        return f"{self._namespace}:{_config_thread_id(config)}:{_config_checkpoint_id(config)}"

    def _serialize(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, default=lambda obj: getattr(obj, "__dict__", str(obj)))

    def _deserialize(self, raw: bytes) -> dict[str, Any]:
        return json.loads(raw.decode("utf-8"))

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        try:
            data = self._redis.get(self._key(config))
            if not data:
                return None
            if not isinstance(data, bytes):
                return None  # type: ignore[unreachable]
            payload = self._deserialize(data)
            checkpoint = payload["checkpoint"]
            metadata = payload["metadata"]
            return CheckpointTuple(
                config=config,
                checkpoint=checkpoint,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning(f"Redis checkpoint get_tuple failed: {exc}, returning None")
            return None

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        if config:
            value = self.get_tuple(config)
            if value:
                yield value
        else:
            yield from ()

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        payload = {
            "checkpoint": checkpoint,
            "metadata": metadata,
            "versions": new_versions,
        }
        try:
            self._redis.setex(self._key(config), self._ttl, self._serialize(payload))
        except Exception as exc:
            logger.warning(f"Redis checkpoint put failed: {exc}")
            # 繼續執行，不拋出異常（允許部分功能失效）
        return config

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        if not writes:
            return
        payload = {
            "writes": list(writes),
            "task_id": task_id,
            "task_path": task_path,
        }
        try:
            self._redis.setex(f"{self._key(config)}:writes", self._ttl, self._serialize(payload))
        except Exception as exc:
            logger.warning(f"Redis checkpoint put_writes failed: {exc}")
            # 繼續執行，不拋出異常

    def delete_thread(self, thread_id: str) -> None:
        try:
            pattern = f"{self._namespace}:{thread_id}:*"
            keys = list(self._redis.scan_iter(match=pattern))
            if keys:
                self._redis.delete(*keys)
        except Exception as exc:
            logger.warning(f"Redis checkpoint delete_thread failed: {exc}")
            # 繼續執行，不拋出異常

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await asyncio.to_thread(self.get_tuple, config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        if config:
            value = await self.aget_tuple(config)
            if value:
                yield value
        return

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await asyncio.to_thread(self.put, config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        await asyncio.to_thread(self.put_writes, config, writes, task_id, task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        await asyncio.to_thread(self.delete_thread, thread_id)


def build_checkpointer(settings: LangChainGraphSettings):
    """根據設定建立對應 checkpointer。"""

    backend = (settings.state_store.backend or "memory").lower()
    if backend == "redis":
        try:
            # 測試 Redis 連接是否可用
            import redis as redis_client

            test_redis = redis_client.Redis.from_url(settings.state_store.redis_url)
            test_redis.ping()
            logger.info("Redis checkpoint 連接成功，使用 Redis 後端")
            return RedisCheckpointSaver(
                redis_url=settings.state_store.redis_url,
                namespace=settings.state_store.namespace,
                ttl_seconds=settings.state_store.ttl_seconds,
            )
        except Exception as exc:  # pragma: no cover - redis 啟動失敗時 fallback
            logger.warning("初始化 Redis checkpoint 失敗，改用 MemorySaver: %s", exc)
            return MemorySaver()
    return MemorySaver()
