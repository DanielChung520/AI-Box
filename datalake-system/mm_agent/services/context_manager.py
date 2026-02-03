# 代碼功能說明: 上下文管理服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""上下文管理服務 - 管理對話上下文和指代解析"""

import logging
import re
from datetime import datetime
from typing import Any, Dict

from ..models import ConversationContext

logger = logging.getLogger(__name__)


class ContextManager:
    """上下文管理器"""

    def __init__(self, max_history_length: int = 10) -> None:
        """初始化上下文管理器

        Args:
            max_history_length: 最大歷史記錄長度
        """
        self._contexts: Dict[str, ConversationContext] = {}
        self._max_history_length = max_history_length
        self._logger = logger

    async def get_context(
        self,
        session_id: str,
    ) -> ConversationContext:
        """獲取上下文

        Args:
            session_id: 會話ID

        Returns:
            對話上下文
        """
        if session_id not in self._contexts:
            self._contexts[session_id] = ConversationContext(
                session_id=session_id,
            )

        return self._contexts[session_id]

    async def update_context(
        self,
        session_id: str,
        instruction: str,
        result: Dict[str, Any],
    ) -> None:
        """更新上下文

        Args:
            session_id: 會話ID
            instruction: 用戶指令
            result: 執行結果
        """
        context = await self.get_context(session_id)

        # 添加歷史記錄
        context.history.append(
            {
                "instruction": instruction,
                "result": result,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 限制歷史記錄長度
        if len(context.history) > self._max_history_length:
            context.history = context.history[-self._max_history_length :]

        # 更新當前查詢和結果
        context.current_query = {
            "instruction": instruction,
            "timestamp": datetime.now().isoformat(),
        }
        context.last_result = result

        # 提取實體（用於指代解析）
        self._extract_entities(context, result)

        # 更新時間戳
        context.updated_at = datetime.now()

    def _extract_entities(
        self,
        context: ConversationContext,
        result: Dict[str, Any],
    ) -> None:
        """從結果中提取實體

        Args:
            context: 對話上下文
            result: 執行結果
        """
        # 提取料號（多種可能的字段位置）
        part_number = None

        # 直接字段
        if "part_number" in result:
            part_number = result["part_number"]
        # 從part_info中提取
        elif "part_info" in result and isinstance(result["part_info"], dict):
            part_number = result["part_info"].get("part_number")
        # 從stock_info中提取
        elif "stock_info" in result and isinstance(result["stock_info"], dict):
            part_number = result["stock_info"].get("part_number")
        # 從result嵌套中提取
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "part_number" in inner_result:
                part_number = inner_result["part_number"]
            elif "part_info" in inner_result and isinstance(inner_result["part_info"], dict):
                part_number = inner_result["part_info"].get("part_number")
            elif "stock_info" in inner_result and isinstance(inner_result["stock_info"], dict):
                part_number = inner_result["stock_info"].get("part_number")

        if part_number:
            context.entities["last_part_number"] = part_number

        # 提取庫存信息
        stock = None
        if "current_stock" in result:
            stock = result["current_stock"]
        elif "stock_info" in result and isinstance(result["stock_info"], dict):
            stock = result["stock_info"].get("current_stock")
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "current_stock" in inner_result:
                stock = inner_result["current_stock"]
            elif "stock_info" in inner_result and isinstance(inner_result["stock_info"], dict):
                stock = inner_result["stock_info"].get("current_stock")

        if stock is not None:
            context.entities["last_stock"] = stock

        # 提取缺料狀態
        is_shortage = None
        if "is_shortage" in result:
            is_shortage = result["is_shortage"]
        elif "analysis" in result and isinstance(result["analysis"], dict):
            is_shortage = result["analysis"].get("is_shortage")
        elif "result" in result and isinstance(result["result"], dict):
            inner_result = result["result"]
            if "is_shortage" in inner_result:
                is_shortage = inner_result["is_shortage"]
            elif "analysis" in inner_result and isinstance(inner_result["analysis"], dict):
                is_shortage = inner_result["analysis"].get("is_shortage")

        if is_shortage is not None:
            context.entities["last_shortage_status"] = is_shortage

    async def resolve_references(
        self,
        instruction: str,
        context: ConversationContext,
    ) -> str:
        """解析指代，將指代替換為實際值

        Args:
            instruction: 用戶指令
            context: 對話上下文

        Returns:
            解析後的指令
        """
        resolved_instruction = instruction

        # 如果指令中沒有料號，但上下文中有，則添加料號
        if "last_part_number" in context.entities:
            part_number = context.entities["last_part_number"]

            # 檢查指令中是否已經包含料號
            if not re.search(r"[A-Z]{2,4}-\d{2,6}", instruction, re.IGNORECASE):
                # 解析「剛才查的那個料號」
                if "剛才" in instruction or "那個" in instruction or "這個" in instruction:
                    # 替換「剛才查的那個料號」等模式
                    resolved_instruction = re.sub(
                        r"(剛才|那個|這個).*料號",
                        f"料號 {part_number}",
                        resolved_instruction,
                    )
                # 解析「它」、「他」
                elif "它" in instruction or "他" in instruction:
                    # 在「它」或「他」後面添加料號
                    resolved_instruction = re.sub(
                        r"([它他])",
                        f"{part_number}",
                        resolved_instruction,
                    )
                # 如果指令中沒有明確的指代，但缺少料號，則在開頭添加
                elif not any(
                    keyword in instruction
                    for keyword in ["料號", "part", "ABC", "XYZ", "查詢", "query"]
                ):
                    # 對於缺少料號的指令，在開頭添加料號
                    resolved_instruction = f"料號 {part_number} {resolved_instruction}"

        return resolved_instruction

    async def clear_context(self, session_id: str) -> None:
        """清除上下文

        Args:
            session_id: 會話ID
        """
        if session_id in self._contexts:
            del self._contexts[session_id]
            self._logger.info(f"已清除會話上下文: {session_id}")
