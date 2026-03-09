# 代碼功能說明: InputValidator - 使用 MoE 進行輸入校正與完整性檢查
# 創建日期: 2026-03-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-09

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ValidationResult:
    corrected_text: str
    is_complete: bool
    corrections: List[str]
    error: Optional[str]


class InputValidator:
    def __init__(self) -> None:
        self._moe: Optional[Any] = None
        try:
            from llm.moe.moe_manager import LLMMoEManager

            self._moe = LLMMoEManager()
            logger.info("InputValidator 初始化成功：MoE 可用")
        except Exception as exc:
            self._moe = None
            logger.warning("InputValidator 初始化失敗：MoE 不可用", error=str(exc))

    async def validate_and_correct(self, text: str) -> ValidationResult:
        if self._moe is None:
            return ValidationResult(
                corrected_text=text,
                is_complete=True,
                corrections=[],
                error="MoE not available",
            )

        system_prompt: str = (
            "判斷以下輸入是否完整、是否有錯字，如有則校正。"
            '回傳 JSON: {"corrected_text": "...", "is_complete": true/false, "corrections": []}'
        )
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
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
                logger.warning("MoE 回傳內容為空，使用原文")
                return ValidationResult(
                    corrected_text=text,
                    is_complete=True,
                    corrections=[],
                    error="Empty MoE content",
                )

            try:
                parsed: Dict[str, Any] = json.loads(content)
            except Exception as exc:
                logger.warning("MoE 回傳 JSON 解析失敗，使用原文", error=str(exc))
                return ValidationResult(
                    corrected_text=text,
                    is_complete=True,
                    corrections=[],
                    error=f"JSON parse error: {exc}",
                )

            corrected_text: str = str(parsed.get("corrected_text", text))
            is_complete_raw: Any = parsed.get("is_complete", True)
            is_complete: bool = bool(is_complete_raw)

            corrections_raw: Any = parsed.get("corrections", [])
            corrections: List[str]
            if isinstance(corrections_raw, list):
                corrections = [str(item) for item in corrections_raw]
            else:
                corrections = []

            return ValidationResult(
                corrected_text=corrected_text,
                is_complete=is_complete,
                corrections=corrections,
                error=None,
            )
        except Exception as exc:
            logger.warning("輸入校正失敗，使用原文", error=str(exc))
            return ValidationResult(
                corrected_text=text,
                is_complete=True,
                corrections=[],
                error=str(exc),
            )
