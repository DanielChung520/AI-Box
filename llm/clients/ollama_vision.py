# 代碼功能說明: Ollama 視覺模型客戶端實現
# 創建日期: 2025-12-06 16:01 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 16:01 (UTC+8)

"""Ollama 視覺模型客戶端實現 - 基於 BaseVisionClient 接口"""

from __future__ import annotations

import base64
from typing import Any, Dict, List, Optional

import structlog

from llm.clients.ollama import OllamaClient, get_ollama_client
from llm.clients.vision_base import BaseVisionClient
from system.infra.config.config import get_config_section

logger = structlog.get_logger(__name__)


class OllamaVisionClient(BaseVisionClient):
    """Ollama 視覺模型客戶端實現"""

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        """
        初始化 Ollama 視覺客戶端

        Args:
            ollama_client: Ollama 客戶端實例（可選，如果不提供則自動創建）
        """
        config = get_config_section("vision", default={}) or {}

        self.ollama_client = ollama_client or get_ollama_client()
        self._default_model = config.get("default_model") or "qwen3-vl:8b"

        # 默認圖片描述提示詞
        self.default_description_prompt = config.get(
            "description_prompt",
            """请详细描述这张图片的内容，包括：
1. 图片中的主要对象和场景
2. 图片中的文字内容（如果有）
3. 图片的整体含义和上下文
4. 图片的视觉特征（颜色、构图等）

请用中文回答，描述要详细且准确。""",
        )

        logger.info(
            "OllamaVisionClient initialized",
            default_model=self._default_model,
        )

    @property
    def provider_name(self) -> str:
        """返回提供商名稱"""
        return "ollama"

    @property
    def default_model(self) -> str:
        """返回默認視覺模型名稱"""
        return self._default_model

    def is_available(self) -> bool:
        """檢查客戶端是否可用"""
        return self.ollama_client is not None and self.ollama_client.is_available()

    def _encode_image_to_base64(self, image_content: bytes) -> str:
        """
        將圖片內容編碼為 base64 字符串

        Args:
            image_content: 圖片內容（字節）

        Returns:
            base64 編碼的字符串
        """
        return base64.b64encode(image_content).decode("utf-8")

    async def describe_image(
        self,
        image_content: bytes,
        prompt: Optional[str] = None,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        描述圖片內容

        Args:
            image_content: 圖片內容（字節）
            prompt: 描述提示詞（可選，使用默認提示詞）
            model: 視覺模型名稱（可選，使用默認模型）
            user_id: 用戶ID（用於追蹤）
            file_id: 文件ID（用於追蹤）
            task_id: 任務ID（用於追蹤）
            **kwargs: 其他參數

        Returns:
            描述結果字典，包含：
            - description: 圖片描述文本
            - confidence: 置信度（如果可用）
            - metadata: 額外元數據
        """
        if not self.is_available():
            raise RuntimeError("Ollama vision client is not available")

        # 使用默認提示詞或提供的提示詞
        description_prompt = prompt or self.default_description_prompt
        vision_model = model or self.default_model

        # 將圖片編碼為 base64
        image_base64 = self._encode_image_to_base64(image_content)

        try:
            # 調用 Ollama chat API，帶圖片
            response = await self.ollama_client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": description_prompt,
                    }
                ],
                images=[image_base64],
                model=vision_model,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="vision",
                **kwargs,
            )

            # 提取描述文本
            description = response.get("content") or response.get("message", "")

            logger.info(
                "圖片描述生成成功",
                model=vision_model,
                description_length=len(description),
                file_id=file_id,
            )

            return {
                "description": description,
                "confidence": None,  # Ollama 不提供置信度，設為 None
                "metadata": {
                    "model": vision_model,
                    "prompt": description_prompt,
                    "image_size": len(image_content),
                },
            }

        except Exception as e:
            logger.error(
                "圖片描述生成失敗",
                model=vision_model,
                error=str(e),
                file_id=file_id,
                exc_info=True,
            )
            raise RuntimeError(f"Failed to describe image: {str(e)}") from e

    async def chat_with_image(
        self,
        messages: List[Dict[str, Any]],
        images: List[bytes],
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        file_id: Optional[str] = None,
        task_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        帶圖片的對話

        Args:
            messages: 消息列表，每個消息包含 'role' 和 'content'
            images: 圖片內容列表（字節）
            model: 視覺模型名稱（可選）
            user_id: 用戶ID（用於追蹤）
            file_id: 文件ID（用於追蹤）
            task_id: 任務ID（用於追蹤）
            **kwargs: 其他參數

        Returns:
            對話結果字典，包含 'content' 或 'message' 字段
        """
        if not self.is_available():
            raise RuntimeError("Ollama vision client is not available")

        vision_model = model or self.default_model

        # 將所有圖片編碼為 base64
        images_base64 = [self._encode_image_to_base64(img) for img in images]

        try:
            # 調用 Ollama chat API，帶圖片
            response = await self.ollama_client.chat(
                messages=messages,
                images=images_base64,
                model=vision_model,
                user_id=user_id,
                file_id=file_id,
                task_id=task_id,
                purpose="vision",
                **kwargs,
            )

            return response

        except Exception as e:
            logger.error(
                "帶圖片的對話失敗",
                model=vision_model,
                error=str(e),
                file_id=file_id,
                exc_info=True,
            )
            raise RuntimeError(f"Failed to chat with image: {str(e)}") from e


# 全局服務實例（懶加載）
_ollama_vision_client: Optional[OllamaVisionClient] = None


def get_ollama_vision_client() -> OllamaVisionClient:
    """獲取 Ollama 視覺客戶端實例（單例模式）"""
    global _ollama_vision_client
    if _ollama_vision_client is None:
        _ollama_vision_client = OllamaVisionClient()
    return _ollama_vision_client
