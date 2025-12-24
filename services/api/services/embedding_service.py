# 代碼功能說明: 向量化服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""向量化服務 - 使用 Ollama 生成文本嵌入向量"""

from __future__ import annotations

import asyncio
import os
from typing import Callable, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)

# 全局服務實例（單例模式）
_embedding_service: Optional["EmbeddingService"] = None


class EmbeddingService:
    """向量化服務類 - 使用 Ollama 生成 embeddings"""

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: int = 10,
        max_retries: int = 3,
        timeout: float = 60.0,
        concurrency_limit: Optional[int] = None,
    ):
        """
        初始化向量化服務

        Args:
            ollama_url: Ollama 服務地址，默認為 http://localhost:11434
            model: Embedding 模型名稱，默認為 nomic-embed-text
            batch_size: 批量處理大小（每批次的文本數量）
            max_retries: 最大重試次數
            timeout: 請求超時時間（秒）
            concurrency_limit: 並發限制（同時進行的請求數，默認為 batch_size * 2）
        """
        # 直接读取配置文件
        import json
        from pathlib import Path

        # 计算配置文件路径（从项目根目录）

        current_file = Path(__file__).resolve()
        # 向上查找直到找到项目根目录（有 config 目录）
        config_path = None
        for parent in [current_file.parent] + list(current_file.parents):
            potential_config = parent / "config" / "config.json"
            if potential_config.exists():
                config_path = potential_config
                break
        if not config_path:
            # 如果找不到，使用相对路径（从项目根目录）
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "config" / "config.json"
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = json.load(f)
                config = full_config.get("embedding", {})
                # 如果 embedding 不存在，从 services.ollama 读取
                if not config and "services" in full_config:
                    ollama_config = full_config["services"].get("ollama", {})
                    if ollama_config:
                        config = {
                            "ollama_url": f"http://{ollama_config.get('host', 'localhost')}:{ollama_config.get('port', 11434)}",
                            "model": ollama_config.get("embedding_model", "nomic-embed-text"),
                        }
        self.ollama_url = (
            ollama_url
            or os.getenv("OLLAMA_URL")
            or config.get("ollama_url")
            or "http://localhost:11434"
        )
        self.model = (
            model
            or os.getenv("OLLAMA_EMBEDDING_MODEL")
            or config.get("model")
            or "nomic-embed-text"
        )
        # 支持環境變量 EMBEDDING_BATCH_SIZE
        env_batch_size = os.getenv("EMBEDDING_BATCH_SIZE")
        config_batch_size = (
            int(env_batch_size) if env_batch_size else config.get("batch_size", 10)  # type: ignore[arg-type]  # env_batch_size 已檢查不為 None
        )
        self.batch_size = batch_size or config_batch_size
        self.max_retries = max_retries or config.get("max_retries", 3)
        self.timeout = timeout or config.get("timeout", 60.0)

        # 並發限制：允許同時進行的請求數（默認為 batch_size * 2，最大100）
        config_concurrency = config.get("concurrency_limit")
        if concurrency_limit is not None:
            self.concurrency_limit = concurrency_limit
        elif config_concurrency is not None:
            self.concurrency_limit = config_concurrency
        else:
            # 默認值：batch_size * 2，但至少50，最大100
            self.concurrency_limit = max(min(self.batch_size * 2, 100), 50)

        # 確保 URL 沒有結尾斜杠
        self.ollama_url = self.ollama_url.rstrip("/")

        logger.info(
            "EmbeddingService initialized",
            ollama_url=self.ollama_url,
            model=self.model,
            batch_size=self.batch_size,
            concurrency_limit=self.concurrency_limit,
        )

    async def generate_embedding(
        self,
        text: str,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> List[float]:
        """
        生成單個文本的嵌入向量

        Args:
            text: 輸入文本
            user_id: 用戶ID（用於追蹤）
            file_id: 文件ID（用於追蹤）
            task_id: 任務ID（用於追蹤）

        Returns:
            嵌入向量列表

        Raises:
            RuntimeError: 如果生成失敗
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.ollama_url}/api/embeddings",
                        json={"model": self.model, "prompt": text},
                    )
                    response.raise_for_status()
                    result = response.json()

                    if "embedding" not in result:
                        raise ValueError(f"Invalid response from Ollama: {result}")

                    embedding = result["embedding"]
                    logger.debug(
                        "Generated embedding",
                        text_length=len(text),
                        embedding_dim=len(embedding),
                    )

                    # 追蹤模型使用（如果提供了user_id）
                    if user_id:
                        try:
                            from services.api.models.model_usage import (
                                ModelPurpose,
                                ModelUsageCreate,
                            )
                            from services.api.services.model_usage_service import (
                                get_model_usage_service,
                            )

                            service = get_model_usage_service()
                            usage = ModelUsageCreate(
                                model_name=self.model,
                                user_id=user_id,
                                model_version=None,  # type: ignore[call-arg]  # model_version 有默認值
                                cost=None,  # type: ignore[call-arg]  # cost 有默認值
                                error_message=None,  # type: ignore[call-arg]  # error_message 有默認值
                                file_id=file_id,
                                task_id=task_id,
                                input_length=len(text),
                                output_length=len(embedding),
                                purpose=ModelPurpose.EMBEDDING,
                                latency_ms=0,  # 無法準確測量，設為0
                                success=True,
                                metadata={},
                            )
                            service.create(usage)
                        except Exception as e:
                            logger.warning(f"Failed to track embedding usage: {e}")

                    return embedding

            except httpx.HTTPStatusError as e:
                logger.warning(
                    "HTTP error generating embedding",
                    attempt=attempt + 1,
                    status_code=e.response.status_code,
                    error=str(e),
                )
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Failed to generate embedding after {self.max_retries} attempts: {e}"
                    ) from e
                await asyncio.sleep(2**attempt)  # 指數退避

            except httpx.RequestError as e:
                logger.warning(
                    "Request error generating embedding",
                    attempt=attempt + 1,
                    error=str(e),
                )
                if attempt == self.max_retries - 1:
                    raise RuntimeError(
                        f"Failed to generate embedding: Connection error: {e}"
                    ) from e
                await asyncio.sleep(2**attempt)

            except Exception as e:
                logger.error(
                    "Unexpected error generating embedding",
                    attempt=attempt + 1,
                    error=str(e),
                )
                raise RuntimeError(f"Failed to generate embedding: {e}") from e

        raise RuntimeError(f"Failed to generate embedding after {self.max_retries} attempts")

    async def generate_embeddings_batch(
        self, texts: List[str], progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[List[float]]:
        """
        批量生成嵌入向量

        Args:
            texts: 文本列表
            progress_callback: 可選的進度回調函數，簽名為 (processed_count: int, total_count: int) -> None

        Returns:
            嵌入向量列表（與輸入文本順序對應）

        Raises:
            RuntimeError: 如果批量生成失敗
        """
        if not texts:
            return []

        # 過濾空文本
        valid_texts = [text for text in texts if text and text.strip()]
        if len(valid_texts) != len(texts):
            logger.warning(
                "Some texts were empty and will be skipped",
                total=len(texts),
                valid=len(valid_texts),
            )

        if not valid_texts:
            raise ValueError("No valid texts provided")

        logger.info(
            "Generating embeddings in batch",
            total_texts=len(valid_texts),
            batch_size=self.batch_size,
            concurrency_limit=self.concurrency_limit,
        )

        # 將文本分成多個批次
        batches: List[List[str]] = []
        for i in range(0, len(valid_texts), self.batch_size):
            batches.append(valid_texts[i : i + self.batch_size])

        # 使用全局 semaphore 限制總並發數（控制同時進行的 embedding 請求數）
        global_semaphore = asyncio.Semaphore(self.concurrency_limit)

        # 追蹤進度（用於回調）
        completed_count = 0
        total_count = len(valid_texts)

        async def process_batch_with_index(
            batch_index: int, batch: List[str]
        ) -> tuple[int, List[List[float]]]:
            """處理單個批次，返回批次索引和結果，並更新進度"""
            nonlocal completed_count
            batch_embeddings = await self._generate_batch_internal(batch, global_semaphore)
            completed_count += len(batch_embeddings)

            # 調用進度回調
            if progress_callback:
                try:
                    progress_callback(completed_count, total_count)
                except Exception as e:
                    logger.warning("Progress callback failed", error=str(e))

            logger.debug(
                "Processed batch",
                batch_index=batch_index + 1,
                total_batches=len(batches),
                batch_size=len(batch),
                completed=completed_count,
                total=total_count,
            )
            return (batch_index, batch_embeddings)

        # 並行處理所有批次（批次之間並行，但總並發數受 global_semaphore 限制）
        tasks = [process_batch_with_index(i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 按批次索引排序結果，確保順序正確
        batch_results: List[tuple[int, List[List[float]]]] = []
        for result in results:
            if isinstance(result, Exception):
                logger.error("Failed to process batch", error=str(result))
                raise RuntimeError(f"Failed to process batch: {result}") from result
            if not isinstance(result, tuple):
                continue  # 跳過非 tuple 結果
            batch_results.append(result)  # type: ignore[arg-type]  # 已檢查為 tuple

        # 排序確保順序
        batch_results.sort(key=lambda x: x[0])

        # 合併所有批次的結果
        embeddings: List[List[float]] = []
        for _, batch_embeddings in batch_results:
            embeddings.extend(batch_embeddings)

        # 處理空文本的位置（保持順序）- 如果過濾了空文本，需要映射回原始位置
        # 注意：當前實現中 valid_texts 和 texts 的順序應該一致，所以這裡不需要特殊處理
        # 但如果未來有變化，可能需要根據 valid_texts 的索引映射回 texts 的位置

        logger.info(
            "Batch embeddings generation completed",
            total_texts=len(valid_texts),
            total_batches=len(batches),
            total_embeddings=len(embeddings),
        )

        return embeddings

    async def _generate_batch_internal(
        self, texts: List[str], semaphore: Optional[asyncio.Semaphore] = None
    ) -> List[List[float]]:
        """
        內部方法：生成一批嵌入向量（並發處理）

        Args:
            texts: 文本列表
            semaphore: 可選的 semaphore 用於控制並發數（如果提供，則使用；否則不限制）

        Returns:
            嵌入向量列表
        """

        # 使用提供的 semaphore 或創建一個不限制的（向後兼容）
        async def generate_one(text: str) -> List[float]:
            if semaphore:
                async with semaphore:
                    return await self.generate_embedding(text)
            else:
                return await self.generate_embedding(text)

        tasks = [generate_one(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理錯誤
        embeddings: List[List[float]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Failed to generate embedding for text",
                    text_index=i,
                    error=str(result),
                )
                raise RuntimeError(
                    f"Failed to generate embedding for text {i}: {result}"
                ) from result
            # result 此時應該是 List[float]，因為已經檢查過不是 Exception
            if isinstance(result, list):
                embeddings.append(result)
            else:
                raise RuntimeError(f"Unexpected result type: {type(result)}")

        return embeddings

    async def is_available(self) -> bool:
        """
        檢查 Ollama 服務是否可用

        Returns:
            如果服務可用返回 True，否則返回 False
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                return True
        except Exception as e:
            logger.warning(
                "Ollama service is not available",
                ollama_url=self.ollama_url,
                error=str(e),
            )
            return False


def get_embedding_service() -> EmbeddingService:
    """獲取向量化服務實例（單例模式）

    Returns:
        EmbeddingService 實例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service() -> None:
    """重置向量化服務實例（主要用於測試）"""
    global _embedding_service
    _embedding_service = None
