# 代碼功能說明: 向量化服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""向量化服務 - 使用 Ollama 生成文本嵌入向量"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Optional

import httpx
import structlog

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# 全局服務實例（單例模式）
_embedding_service: Optional["EmbeddingService"] = None


class EmbeddingService:
    """向量化服務類 - 使用 Ollama 生成 embeddings

    產品級並發控制設計：
    1. 類級別全局 Semaphore：確保所有文件處理共享同一個並發限制
    2. 智能批次大小：batch_size 自動匹配 concurrency_limit，避免資源浪費
    3. 部分失敗容錯：單個 embedding 失敗不影響整個批次
    4. 詳細監控：記錄活躍請求數和並發狀態

    # 向量維度到模型的映射表
    DIMENSION_MODEL_MAP: Dict[int, str] = {
        384: "nomic-embed-text",
        768: "bge-large-zh-v1.5",  # 需要根據實際使用的模型調整
        # 可以添加更多映射
    }"""

    # 向量維度到模型的映射表
    # 可以通過環境變量 EMBEDDING_DIMENSION_MODEL_MAP 配置（JSON 格式）
    DIMENSION_MODEL_MAP: Dict[int, str] = {
        384: "nomic-embed-text:latest",
        768: "nomic-embed-text:latest",
        1024: "quentinz/bge-large-zh-v1.5:latest",
    }

    # 語言到嵌入模型的映射表
    # 中文使用專用模型，英文使用通用模型
    LANGUAGE_MODEL_MAP: Dict[str, str] = {
        "zh": "quentinz/bge-large-zh-v1.5:latest",
        "en": "nomic-embed-text:latest",
        "ja": "qwen3-embedding:latest",
        "ko": "qwen3-embedding:latest",
        "default": "nomic-embed-text:latest",
    }

    # 中文字符正則表達式（用於簡單語言檢測）
    CHINESE_PATTERN = r"[\u4e00-\u9fff]"

    # 類級別全局 Semaphore（所有實例共享）
    _global_semaphore: Optional[asyncio.Semaphore] = None
    _global_concurrency_limit: Optional[int] = None
    _active_requests: int = 0
    _lock: Optional[asyncio.Lock] = None

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """獲取類級別鎖（延遲初始化）"""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @staticmethod
    def detect_language(text: str) -> str:
        """
        檢測文本語言（使用簡單的启发式方法）

        檢測邏輯：
        1. 如果文本中包含中文字符，則判定為中文 (zh)
        2. 否則返回 default（使用通用模型）

        Args:
            text: 待檢測的文本

        Returns:
            語言代碼: 'zh' (中文), 'en' (英文), 或 'default'
        """
        import re

        if not text:
            return "default"

        if re.search(EmbeddingService.CHINESE_PATTERN, text):
            return "zh"

        return "default"

    @classmethod
    def get_model_for_language(cls, language: str) -> str:
        """
        根據語言獲取最適合的嵌入模型

        Args:
            language: 語言代碼 ('zh', 'en', 'ja', 'ko', 'default')

        Returns:
            嵌入模型名稱
        """
        return cls.LANGUAGE_MODEL_MAP.get(language, cls.LANGUAGE_MODEL_MAP["default"])

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
        # MoE 場景名稱
        self._moe_scene = "embedding"
        self._moe_model_config = None

        # 優先使用 MoE 配置
        moe_model = self._get_moe_model_config()
        if moe_model:
            self.model = moe_model.model
            self.timeout = moe_model.timeout
            self._moe_model_config = moe_model
            logger.info(
                "embedding_using_moe_config",
                model=self.model,
                scene=self._moe_scene,
                timeout=self.timeout,
            )
            # 從配置載入 URL
            config = self._load_config()
            self.ollama_url = (
                ollama_url
                or os.getenv("OLLAMA_URL")
                or config.get("ollama_url")
                or "http://localhost:11434"
            )
        else:
            # 向後兼容：使用原有配置
            self._init_model_from_config(ollama_url, model, timeout)

        # 讀取其他配置
        config = self._load_config()

        # 支持環境變量 EMBEDDING_BATCH_SIZE
        env_batch_size = os.getenv("EMBEDDING_BATCH_SIZE")
        config_batch_size = int(env_batch_size) if env_batch_size else config.get("batch_size", 10)
        self.batch_size = batch_size or config_batch_size
        self.max_retries = max_retries or config.get("max_retries", 3)

        # 並發限制：允許同時進行的請求數
        config_concurrency = config.get("concurrency_limit")
        if concurrency_limit is not None:
            self.concurrency_limit = concurrency_limit
        elif config_concurrency is not None:
            self.concurrency_limit = config_concurrency
        else:
            # 默認值：batch_size * 2，但至少10，最大100
            self.concurrency_limit = max(min(self.batch_size * 2, 100), 10)

        # 智能調整 batch_size：確保 batch_size 不超過 concurrency_limit
        # 避免批次內並發超過全局限制
        if self.batch_size > self.concurrency_limit:
            # 修改時間：2026-01-22 - 改為 info 級別，因為這是預期的自動調整行為
            logger.info(
                "batch_size exceeds concurrency_limit, adjusting batch_size",
                original_batch_size=self.batch_size,
                concurrency_limit=self.concurrency_limit,
            )
            self.batch_size = max(self.concurrency_limit, 1)

        # 確保 URL 沒有結尾斜杠
        self.ollama_url = self.ollama_url.rstrip("/")

        # 同步初始化全局 Semaphore（如果尚未初始化）
        # 注意：Semaphore 可以在同步代碼中創建，但實際使用需要在 async 上下文中
        if EmbeddingService._global_semaphore is None:
            EmbeddingService._global_semaphore = asyncio.Semaphore(self.concurrency_limit)
            EmbeddingService._global_concurrency_limit = self.concurrency_limit
            logger.info(
                "Global semaphore initialized synchronously",
                concurrency_limit=self.concurrency_limit,
            )
        elif EmbeddingService._global_concurrency_limit != self.concurrency_limit:
            # 如果 concurrency_limit 改變，記錄警告（實際更新在第一次使用時進行）
            logger.warning(
                "concurrency_limit mismatch detected",
                instance_limit=self.concurrency_limit,
                global_limit=EmbeddingService._global_concurrency_limit,
                note="Semaphore will be updated on first use",
            )

        logger.info(
            "EmbeddingService initialized",
            ollama_url=self.ollama_url,
            model=self.model,
            batch_size=self.batch_size,
            concurrency_limit=self.concurrency_limit,
            global_semaphore_initialized=EmbeddingService._global_semaphore is not None,
            global_concurrency_limit=EmbeddingService._global_concurrency_limit,
        )

    def _get_moe_model_config(self):
        """從 MoE 獲取模型配置"""
        from llm.moe.moe_manager import LLMMoEManager

        try:
            moe_manager = LLMMoEManager()
            result = moe_manager.select_model(self._moe_scene)
            if result:
                return result
        except Exception as e:
            logger.debug(
                "failed_to_get_moe_model_config",
                scene=self._moe_scene,
                error=str(e),
                message="從 MoE 獲取模型配置失敗，使用向後兼容方式",
            )
        return None

    def _load_config(self) -> Dict:
        """載入配置文件"""
        current_file = Path(__file__).resolve()
        config_path = None
        for parent in [current_file.parent] + list(current_file.parents):
            potential_config = parent / "config" / "config.json"
            if potential_config.exists():
                config_path = potential_config
                break
        if not config_path:
            project_root = Path(__file__).parent.parent.parent.parent.parent
            config_path = project_root / "config" / "config.json"
        config = {}
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                full_config = json.load(f)
                config = full_config.get("embedding", {})
                if not config and "services" in full_config:
                    ollama_config = full_config["services"].get("ollama", {})
                    if ollama_config:
                        config = {
                            "ollama_url": f"http://{ollama_config.get('host', 'localhost')}:{ollama_config.get('port', 11434)}",
                            "model": ollama_config.get("embedding_model", "qwen3-embedding:latest"),
                        }
        return config

    def _init_model_from_config(
        self, ollama_url: Optional[str], model: Optional[str], timeout: float
    ):
        """從配置文件初始化模型（向後兼容）"""
        config = self._load_config()

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
            or "qwen3-embedding:latest"
        )
        self.timeout = timeout or config.get("timeout", 60.0)

    def _load_dimension_model_map(self) -> None:
        """
        從環境變量或配置文件加載維度到模型的映射

        環境變量格式：EMBEDDING_DIMENSION_MODEL_MAP='{"384": "nomic-embed-text", "768": "bge-large-zh-v1.5"}'
        """
        import json

        # 從環境變量讀取
        env_map = os.getenv("EMBEDDING_DIMENSION_MODEL_MAP")
        if env_map:
            try:
                env_dict = json.loads(env_map)
                # 將字符串鍵轉換為整數鍵
                for key, value in env_dict.items():
                    try:
                        dimension = int(key)
                        self.DIMENSION_MODEL_MAP[dimension] = value
                    except ValueError:
                        logger.warning(
                            "Invalid dimension in EMBEDDING_DIMENSION_MODEL_MAP",
                            key=key,
                        )
                logger.info(
                    "Loaded dimension model map from environment",
                    map=self.DIMENSION_MODEL_MAP,
                )
            except json.JSONDecodeError as e:
                logger.warning(
                    "Failed to parse EMBEDDING_DIMENSION_MODEL_MAP",
                    error=str(e),
                )

    def get_model_for_dimension(self, dimension: int) -> str:
        """
        根據向量維度獲取對應的模型

        Args:
            dimension: 向量維度

        Returns:
            對應的模型名稱，如果找不到匹配的模型，返回默認模型
        """
        model = self.DIMENSION_MODEL_MAP.get(dimension)
        if model:
            logger.debug(
                "Model selected for dimension",
                dimension=dimension,
                model=model,
            )
            return model

        # 找不到匹配的模型，使用默認模型並記錄警告
        logger.warning(
            "No model mapping found for dimension, using default model",
            dimension=dimension,
            default_model=self.model,
            available_dimensions=list(self.DIMENSION_MODEL_MAP.keys()),
        )
        return self.model

    async def _ensure_global_semaphore(self) -> None:
        """
        確保全局 Semaphore 已初始化並與當前 concurrency_limit 匹配

        如果全局 Semaphore 不存在或 concurrency_limit 已更改，則重新創建。
        這是類級別方法，確保所有實例共享同一個並發限制。
        """
        lock = self._get_lock()
        async with lock:
            if (
                EmbeddingService._global_semaphore is None
                or EmbeddingService._global_concurrency_limit != self.concurrency_limit
            ):
                # 如果 concurrency_limit 改變，需要重新創建 Semaphore
                if EmbeddingService._global_semaphore is not None:
                    logger.info(
                        "Recreating global semaphore due to concurrency_limit change",
                        old_limit=EmbeddingService._global_concurrency_limit,
                        new_limit=self.concurrency_limit,
                    )
                EmbeddingService._global_semaphore = asyncio.Semaphore(self.concurrency_limit)
                EmbeddingService._global_concurrency_limit = self.concurrency_limit
                logger.info(
                    "Global semaphore initialized/updated",
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

        使用全局 Semaphore 控制並發，確保所有文件處理共享同一個並發限制。

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

        # 確保全局 Semaphore 已初始化
        await self._ensure_global_semaphore()

        # 使用全局 Semaphore 控制並發
        semaphore = EmbeddingService._global_semaphore
        if semaphore is None:
            raise RuntimeError("Global semaphore not initialized")

        # 更新活躍請求計數（用於監控）
        lock = self._get_lock()
        async with lock:
            EmbeddingService._active_requests += 1
            current_active = EmbeddingService._active_requests
        logger.debug(
            "Starting embedding request",
            active_requests=current_active,
            concurrency_limit=self.concurrency_limit,
            file_id=file_id,
        )

        try:
            # 在 Semaphore 保護下執行請求
            async with semaphore:
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
                                file_id=file_id,
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
                            file_id=file_id,
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
                            file_id=file_id,
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
                            file_id=file_id,
                        )
                        raise RuntimeError(f"Failed to generate embedding: {e}") from e

            raise RuntimeError(f"Failed to generate embedding after {self.max_retries} attempts")
        finally:
            # 更新活躍請求計數
            lock = self._get_lock()
            async with lock:
                EmbeddingService._active_requests = max(0, EmbeddingService._active_requests - 1)
                current_active = EmbeddingService._active_requests
            logger.debug(
                "Completed embedding request",
                active_requests=current_active,
                concurrency_limit=self.concurrency_limit,
                file_id=file_id,
            )

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

        # 確保全局 Semaphore 已初始化
        await self._ensure_global_semaphore()
        global_semaphore = EmbeddingService._global_semaphore
        if global_semaphore is None:
            raise RuntimeError("Global semaphore not initialized")

        # 追蹤進度（用於回調）
        completed_count = 0
        total_count = len(valid_texts)

        logger.info(
            "Starting batch embeddings generation",
            total_texts=len(valid_texts),
            total_batches=len(batches),
            batch_size=self.batch_size,
            concurrency_limit=self.concurrency_limit,
            active_requests=EmbeddingService._active_requests,
        )

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
        failed_batches: List[tuple[int, Exception]] = []

        for batch_index, result in enumerate(results):
            if isinstance(result, Exception):
                failed_batches.append((batch_index, result))
                logger.error(
                    "Failed to process batch",
                    batch_index=batch_index,
                    error=str(result),
                    error_type=type(result).__name__,
                )
                # 不立即拋出異常，允許部分失敗（產品級容錯）
            elif isinstance(result, tuple):
                batch_results.append(result)  # type: ignore[arg-type]  # 已檢查為 tuple
            else:
                logger.warning(
                    "Unexpected batch result type",
                    batch_index=batch_index,
                    result_type=type(result).__name__,
                )

        # 如果有批次失敗，記錄警告但繼續處理成功的批次
        if failed_batches:
            logger.warning(
                "Some batches failed during embedding generation",
                failed_count=len(failed_batches),
                total_batches=len(batches),
                failed_batch_indices=[idx for idx, _ in failed_batches],
            )
            # 如果所有批次都失敗，才拋出異常
            if len(failed_batches) == len(batches):
                error_msg = f"All {len(batches)} batches failed during embedding generation"
                logger.error(error_msg)
                raise RuntimeError(error_msg) from failed_batches[0][1]

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

        注意：此方法不再創建新的 semaphore，因為 generate_embedding 已經使用全局 Semaphore。
        semaphore 參數保留僅為向後兼容，但實際上不會使用。

        Args:
            texts: 文本列表
            semaphore: 已廢棄，保留僅為向後兼容（實際使用全局 Semaphore）

        Returns:
            嵌入向量列表（可能包含部分失敗，用空列表表示）
        """
        # 注意：generate_embedding 已經使用全局 Semaphore，這裡不需要再次限制
        # 但為了避免批次內過度並發，我們仍然使用 asyncio.gather 來控制批次內的並發
        tasks = [self.generate_embedding(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 處理錯誤：允許部分失敗（產品級容錯）
        embeddings: List[List[float]] = []
        failed_count = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                logger.error(
                    "Failed to generate embedding for text",
                    text_index=i,
                    text_preview=texts[i][:50] if i < len(texts) else "N/A",
                    error=str(result),
                    error_type=type(result).__name__,
                )
                # 使用空列表表示失敗（而不是拋出異常）
                # 這樣可以讓批次繼續處理其他文本
                embeddings.append([])
            elif isinstance(result, list):
                embeddings.append(result)
            else:
                failed_count += 1
                logger.error(
                    "Unexpected result type for embedding",
                    text_index=i,
                    result_type=type(result).__name__,
                )
                embeddings.append([])

        # 如果所有文本都失敗，才拋出異常
        if failed_count == len(texts):
            error_msg = f"All {len(texts)} texts failed during embedding generation in batch"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        elif failed_count > 0:
            logger.warning(
                "Some texts failed during batch embedding generation",
                failed_count=failed_count,
                total_count=len(texts),
                success_count=len(texts) - failed_count,
            )

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
