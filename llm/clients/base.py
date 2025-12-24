# 代碼功能說明: LLM 客戶端基類接口定義
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""定義統一的 LLM 客戶端接口，為後續多 LLM 整合做準備。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseLLMClient(ABC):
    """LLM 客戶端抽象基類，定義統一的接口規範。"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        生成文本。

        Args:
            prompt: 輸入提示詞
            model: 模型名稱（可選，使用默認模型）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            生成結果字典，包含 'text' 或 'content' 字段
        """
        raise NotImplementedError

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        對話生成。

        Args:
            messages: 消息列表，每個消息包含 'role' 和 'content'
            model: 模型名稱（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
            **kwargs: 其他參數

        Returns:
            對話結果字典，包含 'content' 或 'message' 字段
        """
        raise NotImplementedError

    @abstractmethod
    async def embeddings(
        self,
        text: str,
        *,
        model: Optional[str] = None,
        **kwargs: Any,
    ) -> List[float]:
        """
        生成文本嵌入向量。

        Args:
            text: 輸入文本
            model: 嵌入模型名稱（可選）
            **kwargs: 其他參數

        Returns:
            嵌入向量列表
        """
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回提供商名稱。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def default_model(self) -> str:
        """返回默認模型名稱。"""
        raise NotImplementedError

    def is_available(self) -> bool:
        """
        檢查客戶端是否可用。

        Returns:
            如果可用返回 True，否則返回 False
        """
        return True
