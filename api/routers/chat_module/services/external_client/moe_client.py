# 代碼功能說明: MoE 客戶端
# 創建日期: 2026-03-02
# 創建人: Daniel Chung

"""MoE 客戶端 - LLM 對話"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MoEClient:
    """MoE 客戶端 - 調用 LLM 對話服務"""

    def __init__(self):
        """初始化 MoE 客戶端"""
        self._moe_manager = None

    def _get_moe_manager(self):
        """獲取 MoE Manager"""
        if self._moe_manager is None:
            from llm.moe.moe_manager import LLMMoEManager

            self._moe_manager = LLMMoEManager()
        return self._moe_manager

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "auto",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        task_type: str = "chat",
    ) -> Dict[str, Any]:
        """調用 MoE 進行對話

        Args:
            messages: 訊息列表 [{"role": "user", "content": "..."}]
            model: 模型名稱 ("auto" 表示自動選擇)
            temperature: 溫度
            max_tokens: 最大 token 數
            session_id: 會話 ID
            user_id: 用戶 ID
            task_type: 任務類型

        Returns:
            LLM 回覆
        """
        last_message = messages[-1].get("content", "")[:50] if messages else ""
        logger.info(f"[MoEClient] Chat: {last_message}...")

        try:
            moe = self._get_moe_manager()

            # 調用 MoE Manager 的 chat 方法
            result = await moe.chat(
                messages=messages,
                scene=task_type,
                user_id=user_id,
                session_id=session_id,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # 解析結果
            if result and hasattr(result, "content"):
                return {
                    "status": "success",
                    "content": result.content,
                    "model": result.model,
                    "usage": result.usage.dict() if result.usage else None,
                }
            elif isinstance(result, dict):
                return {
                    "status": "success",
                    "content": result.get("content", ""),
                    "model": result.get("model", model),
                }
            else:
                return {
                    "status": "error",
                    "error": "invalid_response",
                    "message": "MoE 返回格式無效",
                    "content": "抱歉，服務返回格式異常。",
                }

        except Exception as e:
            logger.error(f"[MoEClient] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": "unknown",
                "message": str(e),
                "content": "抱歉，服務暫時不可用。",
            }


# 全局實例
_moe_client: Optional[MoEClient] = None


def get_moe_client() -> MoEClient:
    """獲取全局 MoEClient 實例"""
    global _moe_client
    if _moe_client is None:
        _moe_client = MoEClient()
    return _moe_client
