# 代碼功能說明: 指令澄清機制模塊（通用澄清服務）
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""指令澄清機制模塊 - 提供通用的槽位提取和澄清問題生成功能"""

import logging
import re
from typing import Any, Dict, List, Optional

from agents.task_analyzer.llm_router import LLMRouter
from agents.task_analyzer.models import TaskClassificationResult

logger = logging.getLogger(__name__)


class ClarificationResult:
    """澄清結果模型"""

    def __init__(
        self,
        clarification_needed: bool,
        clarification_question: Optional[str] = None,
        missing_slots: Optional[List[str]] = None,
    ):
        self.clarification_needed = clarification_needed
        self.clarification_question = clarification_question
        self.missing_slots = missing_slots or []

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典"""
        return {
            "clarification_needed": self.clarification_needed,
            "clarification_question": self.clarification_question,
            "missing_slots": self.missing_slots,
        }


class ClarificationService:
    """指令澄清服務

    提供通用的槽位提取和澄清問題生成功能，支持多種任務類型。
    """

    def __init__(self):
        """初始化澄清服務"""
        self.llm_router = LLMRouter()

    async def extract_slots(
        self,
        instruction: str,
        task_type: str,
        required_slots: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        提取槽位（通用方法）

        Args:
            instruction: 自然語言指令
            task_type: 任務類型（如 "config", "log_query" 等）
            required_slots: 必需的槽位列表
            context: 上下文信息

        Returns:
            提取的槽位字典
        """
        slots = {}
        missing_slots = []

        # 根據任務類型使用不同的提取策略
        if task_type == "config":
            slots = await self._extract_config_slots(instruction, required_slots, context)
        elif task_type == "log_query":
            slots = await self._extract_log_query_slots(instruction, required_slots, context)
        else:
            # 通用提取：使用關鍵詞匹配
            slots = self._extract_generic_slots(instruction, required_slots, context)

        # 檢查缺失的槽位
        for slot in required_slots:
            if slot not in slots or slots[slot] is None:
                missing_slots.append(slot)

        return {
            "slots": slots,
            "missing_slots": missing_slots,
        }

    async def generate_clarification_question(
        self,
        instruction: str,
        task_type: str,
        missing_slots: List[str],
        context: Optional[Dict[str, Any]] = None,
        classification: Optional[TaskClassificationResult] = None,
    ) -> str:
        """
        生成澄清問題（使用 LLM）

        Args:
            instruction: 原始指令
            task_type: 任務類型
            missing_slots: 缺失的槽位列表
            context: 上下文信息
            classification: 任務分類結果（可選）

        Returns:
            澄清問題文本
        """
        if not missing_slots:
            return ""

        # 根據任務類型構建不同的提示詞
        if task_type == "config":
            return await self._generate_config_clarification_question(
                instruction, missing_slots, context
            )
        elif task_type == "log_query":
            return await self._generate_log_query_clarification_question(
                instruction, missing_slots, context
            )
        else:
            return await self._generate_generic_clarification_question(
                instruction, missing_slots, context, classification
            )

    async def check_clarification_needed(
        self,
        instruction: str,
        task_type: str,
        required_slots: List[str],
        extracted_data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        classification: Optional[TaskClassificationResult] = None,
    ) -> ClarificationResult:
        """
        檢查是否需要澄清（完整流程）

        Args:
            instruction: 自然語言指令
            task_type: 任務類型
            required_slots: 必需的槽位列表
            extracted_data: 已提取的數據
            context: 上下文信息
            classification: 任務分類結果（可選）

        Returns:
            ClarificationResult 對象
        """
        # 檢查缺失的槽位
        missing_slots = []
        for slot in required_slots:
            if slot not in extracted_data or extracted_data[slot] is None:
                missing_slots.append(slot)

        # 如果沒有缺失槽位，不需要澄清
        if not missing_slots:
            return ClarificationResult(clarification_needed=False)

        # 生成澄清問題
        clarification_question = await self.generate_clarification_question(
            instruction, task_type, missing_slots, context, classification
        )

        return ClarificationResult(
            clarification_needed=True,
            clarification_question=clarification_question,
            missing_slots=missing_slots,
        )

    async def manage_context(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        previous_clarifications: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        管理上下文（整合歷史澄清信息）

        Args:
            instruction: 當前指令
            context: 當前上下文
            previous_clarifications: 歷史澄清記錄

        Returns:
            增強後的上下文
        """
        enhanced_context = (context or {}).copy()
        enhanced_context["current_instruction"] = instruction

        if previous_clarifications:
            enhanced_context["clarification_history"] = previous_clarifications
            # 從歷史澄清中提取已確認的槽位
            for clarification in previous_clarifications:
                if "confirmed_slots" in clarification:
                    enhanced_context.update(clarification["confirmed_slots"])

        return enhanced_context

    # ========== 私有方法 ==========

    async def _extract_config_slots(
        self, instruction: str, required_slots: List[str], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """提取配置操作槽位"""
        slots = {}
        instruction_lower = instruction.lower()

        # 提取 level
        if "level" in required_slots:
            if any(keyword in instruction_lower for keyword in ["系統", "system", "全局", "global"]):
                slots["level"] = "system"
            elif any(keyword in instruction_lower for keyword in ["租戶", "tenant"]):
                slots["level"] = "tenant"
            elif any(keyword in instruction_lower for keyword in ["用戶", "user"]):
                slots["level"] = "user"

        # 提取 tenant_id
        if "tenant_id" in required_slots:
            if match := re.search(r"租戶\s*[:：]?\s*(\w+)", instruction_lower):
                slots["tenant_id"] = match.group(1)
            elif context and "tenant_id" in context:
                slots["tenant_id"] = context["tenant_id"]

        # 提取 user_id
        if "user_id" in required_slots:
            if match := re.search(r"用戶\s*[:：]?\s*(\w+)", instruction_lower):
                slots["user_id"] = match.group(1)
            elif context and "user_id" in context:
                slots["user_id"] = context["user_id"]

        return slots

    async def _extract_log_query_slots(
        self, instruction: str, required_slots: List[str], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """提取日誌查詢槽位"""
        slots = {}
        instruction_lower = instruction.lower()

        # 提取 log_type
        if "log_type" in required_slots:
            if re.search(r"任務.*日誌|task.*log", instruction_lower):
                slots["log_type"] = "TASK"
            elif re.search(r"審計.*日誌|audit.*log", instruction_lower):
                slots["log_type"] = "AUDIT"
            elif re.search(r"安全.*日誌|security.*log", instruction_lower):
                slots["log_type"] = "SECURITY"

        # 提取時間範圍（簡化版）
        if "start_time" in required_slots or "end_time" in required_slots:
            from datetime import datetime, timedelta

            if re.search(r"昨天|yesterday", instruction_lower):
                end_time = datetime.utcnow()
                slots["start_time"] = end_time - timedelta(days=1)
                slots["end_time"] = end_time
            elif re.search(r"今天|today", instruction_lower):
                end_time = datetime.utcnow()
                slots["start_time"] = end_time.replace(hour=0, minute=0, second=0, microsecond=0)
                slots["end_time"] = end_time

        return slots

    def _extract_generic_slots(
        self, instruction: str, required_slots: List[str], context: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """通用槽位提取（關鍵詞匹配）"""
        slots = {}
        instruction_lower = instruction.lower()

        for slot in required_slots:
            # 嘗試從上下文中獲取
            if context and slot in context:
                slots[slot] = context[slot]
                continue

            # 嘗試從指令中提取（簡單的關鍵詞匹配）
            if slot in instruction_lower:
                # 這裡可以添加更複雜的提取邏輯
                pass

        return slots

    async def _generate_config_clarification_question(
        self, instruction: str, missing_slots: List[str], context: Optional[Dict[str, Any]]
    ) -> str:
        """生成配置操作澄清問題"""
        questions = []

        if "level" in missing_slots:
            questions.append("要修改哪一層配置？(系統級/租戶級/用戶級)")

        if "scope" in missing_slots:
            questions.append("要操作哪個配置範圍？")

        if "config_data" in missing_slots:
            questions.append("要修改哪些具體配置項？")

        if "tenant_id" in missing_slots:
            questions.append("請提供租戶 ID")

        if "user_id" in missing_slots:
            questions.append("請提供用戶 ID")

        if questions:
            return "請確認：" + " ".join(f"{i+1}. {q}" for i, q in enumerate(questions))

        return "請提供更多信息以完成此配置操作。"

    async def _generate_log_query_clarification_question(
        self, instruction: str, missing_slots: List[str], context: Optional[Dict[str, Any]]
    ) -> str:
        """生成日誌查詢澄清問題"""
        questions = []

        if "log_type" in missing_slots:
            questions.append("要查詢哪種類型的日誌？(任務日誌/審計日誌/安全日誌)")

        if "start_time" in missing_slots or "end_time" in missing_slots:
            questions.append("要查詢哪個時間範圍的日誌？")

        if questions:
            return "請確認：" + " ".join(f"{i+1}. {q}" for i, q in enumerate(questions))

        return "請提供更多信息以完成此日誌查詢。"

    async def _generate_generic_clarification_question(
        self,
        instruction: str,
        missing_slots: List[str],
        context: Optional[Dict[str, Any]],
        classification: Optional[TaskClassificationResult],
    ) -> str:
        """生成通用澄清問題（使用 LLM）"""
        try:
            # 使用 LLM 生成澄清問題
            from llm.clients.factory import LLMClientFactory
            from services.api.models.llm_model import LLMProvider as APILLMProvider

            # 選擇合適的 LLM（使用默認配置）
            provider_enum = APILLMProvider.OPENAI
            client = LLMClientFactory.create_client(provider_enum, use_cache=True)

            system_prompt = """你是一個任務分析助手。當用戶指令缺少必要信息時，生成清晰的澄清問題。

要求：
1. 問題要簡潔明了
2. 一次只問最重要的缺失信息
3. 使用友好的語氣
4. 提供選項（如果適用）"""

            user_prompt = f"""原始指令：{instruction}

缺失的槽位：{', '.join(missing_slots)}

請生成一個澄清問題，幫助用戶補充缺失的信息。只返回問題文本，不要包含其他說明。"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response = await client.chat(messages=messages, model="gpt-4o-mini")

            content = response.get("content") or response.get("text", "")
            if content:
                return content.strip()

        except Exception as e:
            logger.warning(f"Failed to generate clarification question using LLM: {e}")

        # Fallback：返回簡單的澄清問題
        return f"請提供以下信息：{', '.join(missing_slots)}"
