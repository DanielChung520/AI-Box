# 代碼功能說明: Task Analyzer 核心邏輯實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Task Analyzer 核心實現 - 整合任務分析、分類、路由和工作流選擇"""

import uuid
import logging
from typing import Dict, Any, Optional

from agents.task_analyzer.models import (
    TaskAnalysisRequest,
    TaskAnalysisResult,
    TaskType,
    WorkflowType,
)
from agents.task_analyzer.classifier import TaskClassifier
from agents.task_analyzer.workflow_selector import WorkflowSelector
from agents.task_analyzer.llm_router import LLMRouter

logger = logging.getLogger(__name__)


class TaskAnalyzer:
    """Task Analyzer 核心類"""

    def __init__(self):
        """初始化 Task Analyzer"""
        self.classifier = TaskClassifier()
        self.workflow_selector = WorkflowSelector()
        self.llm_router = LLMRouter()

    def analyze(self, request: TaskAnalysisRequest) -> TaskAnalysisResult:
        """
        分析任務並返回分析結果

        Args:
            request: 任務分析請求

        Returns:
            任務分析結果
        """
        logger.info(f"Analyzing task: {request.task[:100]}...")

        # 生成任務ID
        task_id = str(uuid.uuid4())

        # 步驟1: 任務分類
        classification = self.classifier.classify(
            request.task,
            request.context,
        )

        # 步驟2: 工作流選擇
        workflow_selection = self.workflow_selector.select(
            classification,
            request.task,
            request.context,
        )

        # 步驟3: LLM 路由選擇
        llm_routing = self.llm_router.route(
            classification,
            request.task,
            request.context,
        )

        # 判斷是否需要啟動 Agent
        requires_agent = self._should_use_agent(
            classification.task_type,
            request.task,
            request.context,
        )

        # 建議使用的 Agent 列表
        suggested_agents = self._suggest_agents(
            classification.task_type,
            workflow_selection.workflow_type,
        )

        # 構建分析詳情
        analysis_details = {
            "classification": {
                "task_type": classification.task_type.value,
                "confidence": classification.confidence,
                "reasoning": classification.reasoning,
            },
            "workflow": {
                "workflow_type": workflow_selection.workflow_type.value,
                "confidence": workflow_selection.confidence,
                "reasoning": workflow_selection.reasoning,
                "config": workflow_selection.config,
            },
            "llm_routing": {
                "provider": llm_routing.provider.value,
                "model": llm_routing.model,
                "confidence": llm_routing.confidence,
                "reasoning": llm_routing.reasoning,
                "fallback_providers": [p.value for p in llm_routing.fallback_providers],
            },
        }

        # 如果是混合模式，添加 strategy 信息
        if (
            workflow_selection.workflow_type == WorkflowType.HYBRID
            and workflow_selection.strategy
        ):
            strategy = workflow_selection.strategy
            analysis_details["workflow_strategy"] = {
                "mode": strategy.mode,
                "primary": strategy.primary.value,
                "fallback": [f.value for f in strategy.fallback],
                "switch_conditions": strategy.switch_conditions,
                "reasoning": strategy.reasoning,
            }

        # 計算整體置信度（取平均值）
        overall_confidence = (
            classification.confidence
            + workflow_selection.confidence
            + llm_routing.confidence
        ) / 3.0

        logger.info(
            f"Task analysis completed: task_id={task_id}, "
            f"type={classification.task_type.value}, "
            f"workflow={workflow_selection.workflow_type.value}, "
            f"llm={llm_routing.provider.value}, "
            f"requires_agent={requires_agent}"
        )

        return TaskAnalysisResult(
            task_id=task_id,
            task_type=classification.task_type,
            workflow_type=workflow_selection.workflow_type,
            llm_provider=llm_routing.provider,
            confidence=overall_confidence,
            requires_agent=requires_agent,
            analysis_details=analysis_details,
            suggested_agents=suggested_agents,
        )

    def _should_use_agent(
        self,
        task_type: TaskType,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        判斷是否需要啟動 Agent

        Args:
            task_type: 任務類型
            task: 任務描述
            context: 上下文信息

        Returns:
            是否需要啟動 Agent
        """
        # 複雜任務、規劃任務、執行任務通常需要 Agent
        if task_type in [TaskType.COMPLEX, TaskType.PLANNING, TaskType.EXECUTION]:
            return True

        # 簡單查詢可能不需要 Agent
        if task_type == TaskType.QUERY:
            # 檢查任務複雜度
            complexity_keywords = [
                "多步驟",
                "多個",
                "綜合",
                "協作",
                "複雜",
                "multi-step",
                "multiple",
                "comprehensive",
                "collaborate",
                "complex",
            ]
            if any(keyword in task.lower() for keyword in complexity_keywords):
                return True
            return False

        # 審查任務通常需要 Agent
        if task_type == TaskType.REVIEW:
            return True

        # 默認需要 Agent
        return True

    def _suggest_agents(
        self,
        task_type: TaskType,
        workflow_type: Any,  # WorkflowType
    ) -> list[str]:
        """
        建議使用的 Agent 列表

        Args:
            task_type: 任務類型
            workflow_type: 工作流類型

        Returns:
            Agent 名稱列表
        """
        agents = []

        # 根據任務類型建議 Agent
        if task_type == TaskType.PLANNING:
            agents.append("planning_agent")
        if task_type == TaskType.EXECUTION:
            agents.append("execution_agent")
        if task_type == TaskType.REVIEW:
            agents.append("review_agent")

        # 複雜任務可能需要所有 Agent
        if task_type == TaskType.COMPLEX:
            agents.extend(["planning_agent", "execution_agent", "review_agent"])

        # 如果沒有特定建議，至少包含 orchestrator
        if not agents:
            agents.append("orchestrator")

        return agents
