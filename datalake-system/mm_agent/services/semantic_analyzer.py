# 代碼功能說明: 語義分析服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""語義分析服務 - 正則+LLM混合策略"""

import logging
import re
from typing import Any, Dict, Optional

from ..models import SemanticAnalysisResult
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """語義分析服務"""

    def __init__(self, prompt_manager: Optional[PromptManager] = None) -> None:
        """初始化語義分析器

        Args:
            prompt_manager: 提示詞管理器（可選）
        """
        self._prompt_manager = prompt_manager or PromptManager()
        self._logger = logger

        # 定義關鍵詞模式
        self._patterns = {
            "query_part": [
                r"查詢.*料號",
                r"查詢.*物料",
                r"料號.*信息",
                r"料號.*規格",
                r"料號.*供應商",
                r"供應商.*誰",
                r"物料.*信息",
                r"part.*info",
                r"query.*part",
            ],
            "query_stock": [
                r"查詢.*庫存",
                r"庫存.*數量",
                r"還有.*庫存",
                r"庫存.*多少",
                r"多少.*庫存",
                r"stock.*quantity",
                r"current.*stock",
                r"存放在.*哪裡",
                r"存放.*位置",
            ],
            "analyze_shortage": [
                r"缺料",
                r"補貨",
                r"shortage",
                r"需要.*補",
                r"庫存.*不足",
            ],
            "generate_purchase_order": [
                r"生成.*採購單",
                r"創建.*採購單",
                r"purchase.*order",
                r"採購",
            ],
        }

    async def analyze(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SemanticAnalysisResult:
        """語義分析（混合策略）

        Args:
            instruction: 用戶指令
            context: 上下文信息（可選）

        Returns:
            語義分析結果
        """
        # 如果指令中包含料號，優先使用正則表達式（快速）
        if self._is_simple_instruction(instruction):
            result = await self._analyze_with_regex(instruction)
            # 如果正則表達式沒有提取到料號，但上下文中有，則使用上下文的料號
            if (
                result.parameters.get("part_number") is None
                and context
                and context.get("entities")
                and "last_part_number" in context.get("entities", {})
            ):
                result.parameters["part_number"] = context["entities"]["last_part_number"]
            return result

        # 策略2：複雜指令使用LLM（智能）
        result = await self._analyze_with_llm(instruction, context)
        # 如果LLM沒有提取到料號，但上下文中有，則使用上下文的料號
        if (
            result.parameters.get("part_number") is None
            and context
            and context.get("entities")
            and "last_part_number" in context.get("entities", {})
        ):
            result.parameters["part_number"] = context["entities"]["last_part_number"]
        return result

    def _is_simple_instruction(self, instruction: str) -> bool:
        """判斷是否為簡單指令

        Args:
            instruction: 用戶指令

        Returns:
            是否為簡單指令
        """
        # 簡單指令特徵：
        # 1. 長度較短（< 50 字符）
        # 2. 包含明確的關鍵詞和料號
        # 3. 不包含指代或上下文依賴

        if len(instruction) > 50:
            return False

        # 檢查是否包含指代
        if any(word in instruction for word in ["剛才", "那個", "這個", "它", "他"]):
            return False

        # 檢查是否包含明確的料號
        if re.search(r"[A-Z]{2,4}-\d{2,6}", instruction, re.IGNORECASE):
            return True

        return False

    async def _analyze_with_regex(
        self,
        instruction: str,
    ) -> SemanticAnalysisResult:
        """使用正則表達式進行語義分析

        Args:
            instruction: 用戶指令

        Returns:
            語義分析結果
        """
        detected_intent: Optional[str] = None
        confidence = 0.0

        # 識別意圖
        for intent, pattern_list in self._patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, instruction, re.IGNORECASE):
                    detected_intent = intent
                    confidence = 0.8
                    break
            if detected_intent:
                break

        # 提取參數
        part_number = self._extract_part_number(instruction)
        quantity = self._extract_quantity(instruction)

        return SemanticAnalysisResult(
            intent=detected_intent,
            confidence=confidence,
            parameters={
                "part_number": part_number,
                "quantity": quantity,
            },
            original_instruction=instruction,
            clarification_needed=(detected_intent is None),
            clarification_questions=(["請明確您要執行哪個操作？"] if detected_intent is None else []),
        )

    async def _analyze_with_llm(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SemanticAnalysisResult:
        """使用LLM進行語義分析

        Args:
            instruction: 用戶指令
            context: 上下文信息（可選）

        Returns:
            語義分析結果
        """
        try:
            # 構建提示詞
            system_prompt = self._prompt_manager.get_system_prompt()
            user_prompt = self._prompt_manager.build_semantic_analysis_prompt(instruction, context)

            # 調用LLM
            llm_response = await self._prompt_manager.call_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,  # 低溫度，提高確定性
            )

            # 如果LLM調用失敗，回退到正則表達式
            if not llm_response:
                self._logger.warning("LLM調用失敗，回退到正則表達式分析")
                return await self._analyze_with_regex(instruction)

            # 解析LLM響應
            result = self._prompt_manager.parse_llm_response(llm_response)

            return SemanticAnalysisResult(
                intent=result.get("intent"),
                confidence=result.get("confidence", 0.0),
                parameters=result.get("parameters", {}),
                original_instruction=instruction,
                clarification_needed=result.get("clarification_needed", False),
                clarification_questions=result.get("clarification_questions", []),
            )

        except Exception as e:
            # LLM調用失敗，回退到正則表達式
            self._logger.warning(f"LLM語義分析失敗，回退到正則表達式: {e}")
            return await self._analyze_with_regex(instruction)

    def _extract_part_number(self, instruction: str) -> Optional[str]:
        """提取料號

        Args:
            instruction: 用戶指令

        Returns:
            提取的料號，如果未找到則返回None
        """
        # 模式1：ABC-123 格式
        pattern1 = r"([A-Z]{2,4}-\d{2,6})"
        match = re.search(pattern1, instruction, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        # 模式2：料號 ABC-123
        pattern2 = r"料號[：:]\s*([A-Z0-9-]+)"
        match = re.search(pattern2, instruction, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        return None

    def _extract_quantity(self, instruction: str) -> Optional[int]:
        """提取數量

        Args:
            instruction: 用戶指令

        Returns:
            提取的數量，如果未找到則返回None
        """
        # 先提取料號，避免從料號中提取數量
        part_number = self._extract_part_number(instruction)

        # 模式：數字 + 單位（件、個、PCS等）
        # 排除料號中的數字（如ABC-123中的123）
        pattern = r"(\d+)\s*(?:件|個|PCS|pcs|unit|units)"
        matches = list(re.finditer(pattern, instruction, re.IGNORECASE))

        for match in matches:
            # 檢查這個數字是否在料號中
            match_start = match.start()
            match_end = match.end()
            matched_text = instruction[max(0, match_start - 10) : match_end + 10]

            # 如果匹配的數字在料號附近（前後10個字符內），跳過
            if part_number and part_number.replace("-", "").replace("_", "") in matched_text:
                continue

            try:
                quantity = int(match.group(1))
                # 數量應該在合理範圍內（1-1000000）
                if 1 <= quantity <= 1000000:
                    return quantity
            except ValueError:
                continue

        return None
