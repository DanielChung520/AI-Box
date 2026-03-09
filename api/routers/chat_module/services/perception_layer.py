# 代碼功能說明: PerceptionLayer - 感知層（指代消解 + 省略消解 + 輸入校正）
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import structlog

from agents.services.entity_memory.entity_memory_service import EntityMemoryService
from api.routers.chat_module.services.input_validator import InputValidator

logger = structlog.get_logger(__name__)


@dataclass
class PerceptionResult:
    original_text: str
    resolved_text: str
    corrected_text: str
    is_complete: bool
    perception_metadata: Dict[str, Any]
    latency_ms: float


class PerceptionLayer:
    def __init__(self) -> None:
        self._entity_memory: Optional[EntityMemoryService] = None
        self._input_validator: InputValidator = InputValidator()
        self._moe: Optional[Any] = None

        try:
            self._entity_memory = EntityMemoryService()
            logger.info("PerceptionLayer 初始化成功：EntityMemoryService 可用")
        except Exception as exc:
            self._entity_memory = None
            logger.warning("PerceptionLayer 初始化警告：EntityMemoryService 不可用", error=str(exc))

        try:
            from llm.moe.moe_manager import LLMMoEManager

            self._moe = LLMMoEManager()
            logger.info("PerceptionLayer 初始化成功：MoE 可用（省略消解）")
        except Exception as exc:
            self._moe = None
            logger.warning("PerceptionLayer 初始化警告：MoE 不可用（省略消解停用）", error=str(exc))

    async def perceive(
        self,
        user_text: str,
        session_id: str,
        user_id: str,
        context_messages: Optional[List[Dict[str, Any]]] = None,
    ) -> PerceptionResult:
        total_start: float = time.perf_counter()
        coref_latency_ms: float = 0.0
        ellipsis_latency_ms: float = 0.0
        validation_latency_ms: float = 0.0

        original_text: str = user_text
        resolved_text: str = user_text
        corrected_text: str = user_text
        is_complete: bool = True
        corrections: List[str] = []
        errors: List[str] = []

        try:
            # Step 1: 指代消解（EntityMemory 基於代詞匹配）
            coref_start: float = time.perf_counter()
            try:
                resolved_text = await self._resolve_coreference(user_text, session_id, user_id)
            except Exception as exc:
                resolved_text = user_text
                errors.append(f"coreference_step_error: {exc}")
                logger.warning("感知層指代消解步驟失敗，降級使用原文", error=str(exc))
            finally:
                coref_latency_ms = (time.perf_counter() - coref_start) * 1000

            # Step 2: 省略消解（LLM 基於對話上下文補全省略語義）
            # 當指代消解未改寫（resolved_text == 原文）且有上下文時，嘗試省略消解
            ellipsis_start: float = time.perf_counter()
            try:
                if resolved_text == user_text and context_messages:
                    ellipsis_result = await self._resolve_ellipsis(user_text, context_messages)
                    if ellipsis_result and ellipsis_result != user_text:
                        resolved_text = ellipsis_result
                        logger.info(
                            "省略消解成功",
                            original=user_text[:50],
                            resolved=resolved_text[:50],
                        )
            except Exception as exc:
                errors.append(f"ellipsis_step_error: {exc}")
                logger.warning("感知層省略消解步驟失敗，降級使用原文", error=str(exc))
            finally:
                ellipsis_latency_ms = (time.perf_counter() - ellipsis_start) * 1000

            # Step 3: 輸入校正（MoE 檢查拼寫與完整性）
            validation_start: float = time.perf_counter()
            try:
                corrected_text, is_complete, corrections = await self._validate_input(resolved_text)
            except Exception as exc:
                corrected_text = resolved_text
                is_complete = True
                corrections = []
                errors.append(f"validation_step_error: {exc}")
                logger.warning("感知層輸入校正步驟失敗，降級使用消解文本", error=str(exc))
            finally:
                validation_latency_ms = (time.perf_counter() - validation_start) * 1000
        except Exception as exc:
            resolved_text = user_text
            corrected_text = user_text
            is_complete = True
            corrections = []
            errors.append(f"perceive_fallback_error: {exc}")
            logger.warning("感知層整體失敗，使用完整降級策略", error=str(exc))

        total_latency_ms: float = (time.perf_counter() - total_start) * 1000
        metadata: Dict[str, Any] = {
            "coreference_latency_ms": coref_latency_ms,
            "ellipsis_latency_ms": ellipsis_latency_ms,
            "validation_latency_ms": validation_latency_ms,
            "corrections": corrections,
            "errors": errors,
            "entity_memory_available": self._entity_memory is not None,
            "moe_available": self._moe is not None,
        }

        return PerceptionResult(
            original_text=original_text,
            resolved_text=resolved_text,
            corrected_text=corrected_text,
            is_complete=is_complete,
            perception_metadata=metadata,
            latency_ms=total_latency_ms,
        )

    async def _resolve_coreference(self, text: str, session_id: str, user_id: str) -> str:
        if self._entity_memory is None:
            return text

        try:
            result: Any = await self._entity_memory.resolve_coreference(
                query=text,
                session_id=session_id,
                user_id=user_id,
            )
            resolved_query: Any = getattr(result, "resolved_query", None)
            if isinstance(resolved_query, str) and resolved_query.strip():
                return resolved_query
            return text
        except Exception as exc:
            logger.warning("指代消解失敗，回退原文", error=str(exc))
            return text

    async def _resolve_ellipsis(
        self,
        user_text: str,
        context_messages: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        省略消解：基於對話上下文，使用 LLM 將省略查詢還原為完整查詢。

        例：
        - 上下文: 「幫我查一下NI001的庫存」→ 回覆了 NI001 庫存
        - 用戶: 「那NI002呢？」
        - 消解: 「幫我查一下NI002的庫存」
        """
        if self._moe is None:
            return None

        # 只取最近 4 條 messages（2 輪）作為上下文，避免過長
        recent_messages = context_messages[-4:] if len(context_messages) > 4 else context_messages

        # 構建上下文摘要
        context_lines: List[str] = []
        for msg in recent_messages:
            role = msg.get("role", "unknown")
            content = str(msg.get("content", ""))[:200]
            if role == "user":
                context_lines.append(f"用戶: {content}")
            elif role == "assistant":
                context_lines.append(f"助手: {content}")

        if not context_lines:
            return None

        context_text = "\n".join(context_lines)

        system_prompt = (
            "你是一個查詢改寫助手。你的任務是根據對話上下文，將省略或指代的查詢還原為完整、獨立的查詢。\n"
            "\n"
            "規則：\n"
            "1. 如果用戶的查詢已經是完整的（不需要上下文就能理解），直接返回原文\n"
            "2. 如果用戶的查詢包含省略（如「那X呢？」「換成X」），根據上下文補全為完整查詢\n"
            "3. 保持業務用語不變（料號、品名等專有名詞不要修改）\n"
            "4. 只返回改寫後的查詢文本，不要解釋\n"
            "\n"
            "範例：\n"
            "上下文: 用戶「幫我查一下NI001的庫存」→ 助手回覆了NI001的庫存數據\n"
            "用戶: 「那NI002呢？」\n"
            "改寫: 「幫我查一下NI002的庫存」\n"
            "\n"
            "範例：\n"
            "上下文: 用戶「查詢料號10-0001的品名和規格」→ 助手回覆了品名規格\n"
            "用戶: 「10-0002的呢？」\n"
            "改寫: 「查詢料號10-0002的品名和規格」"
        )

        user_prompt = (
            f"對話上下文：\n{context_text}\n\n"
            f"用戶當前查詢：{user_text}\n\n"
            "請將用戶當前查詢改寫為完整、獨立的查詢（如果已經完整則返回原文）："
        )

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response: Dict[str, Any] = await asyncio.wait_for(
                self._moe.chat(
                    messages=messages,
                    model=None,
                    temperature=0.1,
                    max_tokens=256,
                ),
                timeout=10.0,
            )
            content: str = str(response.get("content", "")).strip()

            if not content:
                logger.warning("省略消解 MoE 回傳內容為空")
                return None

            # 清理可能的引號包裹
            if content.startswith(("「", '"', "'")) and content.endswith(("」", '"', "'")):
                content = content[1:-1].strip()

            # 如果 LLM 返回的跟原文一樣，說明不需要改寫
            if content == user_text:
                return None

            logger.info(
                "省略消解 LLM 改寫完成",
                original=user_text[:50],
                rewritten=content[:50],
            )
            return content

        except asyncio.TimeoutError:
            logger.warning("省略消解超時（10s）")
            return None
        except Exception as exc:
            logger.warning("省略消解 LLM 調用失敗", error=str(exc))
            return None

    async def _validate_input(self, text: str) -> Tuple[str, bool, List[str]]:
        try:
            result = await self._input_validator.validate_and_correct(text)
            return result.corrected_text, result.is_complete, result.corrections
        except Exception as exc:
            logger.warning("輸入驗證失敗，回退原文", error=str(exc))
            return text, True, []
