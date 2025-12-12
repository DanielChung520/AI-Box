# 代碼功能說明: 向量化服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""向量化服務 - 使用 Ollama 生成文本嵌入向量"""

from __future__ import annotations

import os
import asyncio
from typing import List, Optional
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
    ):
        """
        初始化向量化服務

        Args:
            ollama_url: Ollama 服務地址，默認為 http://localhost:11434
            model: Embedding 模型名稱，默認為 nomic-embed-text
            batch_size: 批量處理大小
            max_retries: 最大重試次數
            timeout: 請求超時時間（秒）
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
                            "model": ollama_config.get(
                                "embedding_model", "nomic-embed-text"
                            ),
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
        self.batch_size = batch_size or config.get("batch_size", 10)
        self.max_retries = max_retries or config.get("max_retries", 3)
        self.timeout = timeout or config.get("timeout", 60.0)

        # 確保 URL 沒有結尾斜杠
        self.ollama_url = self.ollama_url.rstrip("/")

        logger.info(
            "EmbeddingService initialized",
            ollama_url=self.ollama_url,
            model=self.model,
            batch_size=self.batch_size,
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
                            from services.api.services.model_usage_service import (
                                get_model_usage_service,
                            )
                            from services.api.models.model_usage import (
                                ModelUsageCreate,
                                ModelPurpose,
                            )

                            service = get_model_usage_service()
                            usage = ModelUsageCreate(
                                model_name=self.model,
                                user_id=user_id,
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

        raise RuntimeError(
            f"Failed to generate embedding after {self.max_retries} attempts"
        )

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量生成嵌入向量

        Args:
            texts: 文本列表

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
        )

        embeddings: List[List[float]] = []

        # 分批處理
        for i in range(0, len(valid_texts), self.batch_size):
            batch = valid_texts[i : i + self.batch_size]
            batch_embeddings = await self._generate_batch_internal(batch)

            # 處理空文本的位置（保持順序）
            if len(valid_texts) != len(texts):
                # 如果過濾了空文本，需要映射回原始位置
                for j, text in enumerate(batch):
                    embeddings.append(batch_embeddings[j])
            else:
                embeddings.extend(batch_embeddings)

            logger.debug(
                "Processed batch",
                batch_index=i // self.batch_size + 1,
                total_batches=(len(valid_texts) + self.batch_size - 1)
                // self.batch_size,
            )

        return embeddings

    async def _generate_batch_internal(self, texts: List[str]) -> List[List[float]]:
        """
        內部方法：生成一批嵌入向量（並發處理）

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        # 使用 asyncio.gather 並發處理，但限制並發數
        semaphore = asyncio.Semaphore(self.batch_size)

        async def generate_with_semaphore(text: str) -> List[float]:
            async with semaphore:
                return await self.generate_embedding(text)

        tasks = [generate_with_semaphore(text) for text in texts]
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
