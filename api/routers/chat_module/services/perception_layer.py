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
            "你是一個查詢改寫助手。你的任務是根據對話上下文，判斷用戶查詢是否為省略句，並在需要時還原為完整查詢。\n"
            "\n"
            "## 核心原則（最重要）\n"
            "- 如果用戶查詢本身已經包含明確的【查詢對象】和【查詢動作/類型】，它就是完整句，必須原封不動返回\n"
            "- 只有當用戶查詢缺少關鍵信息（省略了動作、對象、或類型），才根據上下文補全\n"
            "- 絕對不能更改用戶明確提到的料號、品名、數字等實體\n"
            "- 絕對不能更改用戶明確提到的查詢類型（庫存→庫存，工單→工單）\n"
            "\n"
            "## 判斷規則\n"
            "1. 完整句（直接返回原文，不做任何修改）：\n"
            "   - 包含料號/品名 + 查詢類型 → 完整句\n"
            "   - 例：「幫我查NI005的庫存」→ 完整句，直接返回「幫我查NI005的庫存」\n"
            "   - 例：「查詢料號10-0001的品名和規格」→ 完整句，直接返回原文\n"
            "   - 例：「幫我查一下NI003的工單狀態」→ 完整句，直接返回原文\n"
            "2. 省略句（需要根據上下文補全）：\n"
            "   - 「那NI002呢？」→ 缺少查詢類型，從上下文繼承\n"
            "   - 「NI003也查一下」→ 缺少查詢類型，從上下文繼承\n"
            "   - 「10-0002的呢？」→ 缺少查詢類型，從上下文繼承\n"
            "   - 「那工單呢？」→ 缺少查詢對象，從上下文繼承\n"
            "\n"
            "## 輸出要求\n"
            "- 只返回改寫後的查詢文本（或原文），不要解釋\n"
            "- 保持業務用語不變（料號、品名等專有名詞不要修改）\n"
            "\n"
            "## 範例\n"
            "上下文: 用戶「幫我查一下NI001的庫存」→ 助手回覆了NI001的庫存數據\n"
            "用戶: 「那NI002呢？」\n"
            "改寫: 「幫我查一下NI002的庫存」\n"
            "\n"
            "上下文: 用戶「幫我查一下NI001的庫存」→ 助手回覆了庫存數據\n"
            "用戶: 「幫我查NI005的庫存」\n"
            "改寫: 「幫我查NI005的庫存」（已完整，原封不動返回）\n"
            "\n"
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

            # 防護性檢查：如果 LLM 返回的是解釋性文字而非查詢，嘗試從中提取改寫結果
            # 跡象：包含解釋性詞語
            explanation_markers = ["根據上下文", "已經完整", "不需要改寫", "不需要改", "因此", "所以", "判斷", "核心原則", "判斷規則"]
            if any(marker in content for marker in explanation_markers):
                # 嘗試從解釋文字中提取實際改寫查詢
                extracted = self._extract_query_from_explanation(content, user_text)
                if extracted:
                    logger.info(
                        "省略消解 LLM 返回解釋文字，成功提取改寫查詢",
                        original=user_text[:50],
                        extracted=extracted[:50],
                    )
                    content = extracted
                else:
                    logger.info(
                        "省略消解 LLM 返回了解釋文字且無法提取查詢，丟棄結果使用原文",
                        original=user_text[:50],
                        llm_response=content[:80],
                    )
                    return None

            # 如果改寫結果長度超過原文 3 倍，很可能是解釋而非查詢
            if len(content) > len(user_text) * 3:
                logger.info(
                    "省略消解 LLM 返回內容過長，可能非查詢文本，丟棄結果",
                    original_len=len(user_text),
                    rewritten_len=len(content),
                )
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


    def _extract_query_from_explanation(self, explanation: str, original_text: str) -> Optional[str]:
        """
        從 LLM 的解釋性回覆中提取實際的改寫查詢。

        LLM 有時會先解釋再給答案，例如：
        "根據上下文，用戶查詢缺少查詢類型。從上下文繼承，幫我查一下NI002的庫存。\n\n因此，改寫後的查詢是：幫我查"
        我們要嘗試提取出「幫我查一下NI002的庫存」。
        """
        import re

        # 策略 1：尋找「查詢是：」「改寫為：」「結果是：」等標記後的內容
        result_markers = [
            r"查詢是[:：]\s*(.+)",
            r"改寫為[:：]\s*(.+)",
            r"改寫後[^:：]*[:：]\s*(.+)",
            r"結果[:：]\s*(.+)",
            r"完整查詢[:：]\s*(.+)",
        ]
        for pattern in result_markers:
            match = re.search(pattern, explanation)
            if match:
                candidate = match.group(1).strip()
                # 清理引號
                if candidate.startswith(("「", '"', "'")) and candidate.endswith(("」", '"', "'")):
                    candidate = candidate[1:-1].strip()
                if candidate and len(candidate) >= 4:
                    return candidate

        # 策略 2：尋找解釋中包含原文實體（料號）的完整查詢句
        # 從原文提取實體（如 NI002、10-0001 等）
        entity_pattern = re.search(r'([A-Za-z]{0,3}\d[A-Za-z0-9\-]+)', original_text)
        if entity_pattern:
            entity = entity_pattern.group(1)
            # 在解釋文字中尋找包含此實體的查詢句
            # 查找簡短的包含實體的句子（分行或分句）
            # 排除解釋性句子（包含「因為」「缺少」「發現」「判斷」等）
            explanation_words = ["因為", "缺少", "發現", "判斷", "不需要", "已經完整", "根據", "規則"]
            sentences = re.split(r'[\n。]', explanation)
            for sent in sentences:
                sent = sent.strip()
                if entity in sent and 4 <= len(sent) <= 30:
                    # 跳過解釋性句子
                    if any(w in sent for w in explanation_words):
                        continue
                    # 清理前置詞
                    cleaned = re.sub(r'^(從上下文繼承|因此)[,，\s]*', '', sent).strip()
                    if cleaned and len(cleaned) >= 4:
                        return cleaned

        return None

    async def _validate_input(self, text: str) -> Tuple[str, bool, List[str]]:
        try:
            result = await self._input_validator.validate_and_correct(text)
            return result.corrected_text, result.is_complete, result.corrections
        except Exception as exc:
            logger.warning("輸入驗證失敗，回退原文", error=str(exc))
            return text, True, []
