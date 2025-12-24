# 代碼功能說明: 視覺模型客戶端抽象基類
# 創建日期: 2025-12-06 16:01 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 16:01 (UTC+8)

"""視覺模型客戶端抽象基類 - 定義統一的視覺模型接口規範"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseVisionClient(ABC):
    """視覺模型客戶端抽象基類，定義統一的接口規範"""

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供商名稱"""
        raise NotImplementedError

    @property
    @abstractmethod
    def default_model(self) -> str:
        """返回默認視覺模型名稱"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用

        Returns:
            如果可用返回 True，否則返回 False
        """
        return True
