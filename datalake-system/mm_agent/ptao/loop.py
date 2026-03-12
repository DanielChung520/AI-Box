# 代碼功能說明: P-T-A-O 迴圈核心邏輯
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

import time
from typing import Any, Dict

from agents.services.protocol.base import AgentServiceRequest
from mm_agent.models import Responsibility, SemanticAnalysisResult

from .models import DecisionEntry, DecisionLog, Observation, PTAOResult, ThoughtTrace
from .responsibility_registry import ResponsibilityRegistry


class PTAOLoop:
    def __init__(self, registry: ResponsibilityRegistry) -> None:
        self._registry = registry

    async def run(
        self,
        responsibility: Responsibility,
        semantic_result: SemanticAnalysisResult,
        request: AgentServiceRequest,
        user_instruction: str,
    ) -> PTAOResult:
        decision_log = DecisionLog()

        complexity = self._determine_complexity(responsibility)
        decision_log.add_entry(
            DecisionEntry(
                phase="plan",
                action="判定執行複雜度",
                rationale=(
                    f"責任類型={responsibility.type}、步驟數={len(responsibility.steps)}，"
                    f"判定為 {complexity}"
                ),
            )
        )

        thought = self._build_thought_trace(responsibility, semantic_result, complexity)
        decision_log.add_entry(
            DecisionEntry(
                phase="think",
                action="生成思考軌跡",
                rationale="以規則推理說明路徑選擇與參數充分性",
            )
        )

        t0 = time.monotonic()
        raw_result: Dict[str, Any] = {}
        observation_success = False
        observation_error: str | None = None

        handler = self._registry.get_handler(responsibility.type)
        if handler is None:
            observation_error = f"未知的職責類型: {responsibility.type}"
            decision_log.add_entry(
                DecisionEntry(
                    phase="act",
                    action="查找並執行 handler",
                    rationale=observation_error,
                )
            )
        else:
            try:
                raw_result = await handler(
                    responsibility,
                    semantic_result,
                    request,
                    user_instruction,
                )
                observation_success = True
                if isinstance(raw_result, dict) and raw_result.get("success") is False:
                    observation_success = False
                    observation_error = str(raw_result.get("error", "執行失敗"))
                    # 保留需要澄清的結果（Guard 攔截、意圖不清晰等）
                    # 清空 raw_result 會導致 needs_clarification 等欄位丟失
                    if not raw_result.get("needs_clarification"):
                        raw_result = {}
                decision_log.add_entry(
                    DecisionEntry(
                        phase="act",
                        action="查找並執行 handler",
                        rationale=(
                            "成功執行職責 handler"
                            if observation_success
                            else f"handler 回傳失敗: {observation_error}"
                        ),
                    )
                )
            except Exception as exc:  # noqa: BLE001
                observation_success = False
                observation_error = str(exc)
                raw_result = {}
                decision_log.add_entry(
                    DecisionEntry(
                        phase="act",
                        action="查找並執行 handler",
                        rationale=f"handler 執行例外: {observation_error}",
                    )
                )

        duration_ms = (time.monotonic() - t0) * 1000
        observation = Observation(
            source=responsibility.type,
            success=observation_success,
            data=raw_result if observation_success else None,
            error=observation_error if not observation_success else None,
            duration_ms=duration_ms,
        )
        decision_log.add_entry(
            DecisionEntry(
                phase="observe",
                action="封裝執行觀察結果",
                rationale=(
                    f"success={observation.success}，duration_ms={observation.duration_ms:.3f}"
                ),
            )
        )

        return PTAOResult(
            thought=thought,
            observation=observation,
            decision_log=decision_log,
            raw_result=raw_result,
        )

    def _determine_complexity(self, responsibility: Responsibility) -> str:
        if responsibility.type in {"analyze_shortage", "generate_purchase_order"}:
            return "complex"
        if len(responsibility.steps) > 1:
            return "complex"
        return "simple"

    def _build_thought_trace(
        self,
        responsibility: Responsibility,
        semantic_result: SemanticAnalysisResult,
        complexity: str,
    ) -> ThoughtTrace:
        has_params = bool(semantic_result.parameters)
        parameter_status = "參數充足" if has_params else "參數不足"
        reasoning = (
            "根據規則推理判定執行路徑；"
            f"責任類型為 {responsibility.type}，步驟數 {len(responsibility.steps)}，"
            f"複雜度為 {complexity}；{parameter_status}。"
        )
        intent_summary = (
            f"intent={semantic_result.intent}, responsibility={responsibility.type}, "
            f"confidence={semantic_result.confidence:.2f}"
        )
        return ThoughtTrace(
            reasoning=reasoning,
            intent_summary=intent_summary,
            complexity=complexity,
        )


async def run_ptao_cycle(
    registry: ResponsibilityRegistry,
    responsibility: Responsibility,
    semantic_result: SemanticAnalysisResult,
    request: AgentServiceRequest,
    user_instruction: str,
) -> PTAOResult:
    return await PTAOLoop(registry=registry).run(
        responsibility=responsibility,
        semantic_result=semantic_result,
        request=request,
        user_instruction=user_instruction,
    )
