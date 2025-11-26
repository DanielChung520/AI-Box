# 代碼功能說明: 工作流選擇器實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""工作流選擇器 - 實現工作流選擇邏輯"""

import logging
from typing import Dict, Any, Optional

from agents.task_analyzer.models import (
    TaskType,
    WorkflowType,
    WorkflowSelectionResult,
    TaskClassificationResult,
)

logger = logging.getLogger(__name__)


class WorkflowSelector:
    """工作流選擇器"""

    def __init__(self):
        """初始化工作流選擇器"""
        # 定義任務類型到工作流類型的映射規則
        self.workflow_rules = {
            TaskType.QUERY: {
                WorkflowType.LANGCHAIN: 0.8,  # 查詢任務優先使用 LangChain
                WorkflowType.CREWAI: 0.3,
                WorkflowType.AUTOGEN: 0.2,
            },
            TaskType.EXECUTION: {
                WorkflowType.LANGCHAIN: 0.7,  # 執行任務優先使用 LangChain
                WorkflowType.AUTOGEN: 0.6,
                WorkflowType.CREWAI: 0.4,
            },
            TaskType.REVIEW: {
                WorkflowType.LANGCHAIN: 0.9,  # 審查任務優先使用 LangChain
                WorkflowType.CREWAI: 0.5,
                WorkflowType.AUTOGEN: 0.3,
            },
            TaskType.PLANNING: {
                WorkflowType.AUTOGEN: 0.8,  # 規劃任務優先使用 AutoGen
                WorkflowType.CREWAI: 0.7,
                WorkflowType.LANGCHAIN: 0.5,
            },
            TaskType.COMPLEX: {
                WorkflowType.HYBRID: 0.9,  # 複雜任務使用混合模式
                WorkflowType.CREWAI: 0.7,
                WorkflowType.AUTOGEN: 0.6,
            },
        }

    def select(
        self,
        task_classification: TaskClassificationResult,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> WorkflowSelectionResult:
        """
        選擇合適的工作流

        Args:
            task_classification: 任務分類結果
            task: 任務描述
            context: 上下文信息

        Returns:
            工作流選擇結果
        """
        logger.info(
            f"Selecting workflow for task type: {task_classification.task_type.value}"
        )

        task_type = task_classification.task_type

        # 獲取該任務類型的工作流規則
        if task_type not in self.workflow_rules:
            # 默認使用 LangChain
            workflow_type = WorkflowType.LANGCHAIN
            confidence = 0.5
            reasoning = f"未知任務類型 {task_type.value}，默認使用 LangChain 工作流"
        else:
            rules = self.workflow_rules[task_type]

            # 考慮上下文中的工作流偏好
            if context and "preferred_workflow" in context:
                preferred = context["preferred_workflow"]
                if preferred in rules:
                    rules[WorkflowType(preferred)] += 0.2

            # 選擇得分最高的工作流
            workflow_type = max(rules.items(), key=lambda x: x[1])[0]
            confidence = rules[workflow_type]
            reasoning = (
                f"根據任務類型 {task_type.value}，選擇 {workflow_type.value} 工作流，"
                f"置信度 {confidence:.2f}"
            )

        # 構建工作流配置
        config = self._build_workflow_config(workflow_type, task_type, context)

        logger.info(
            f"Selected workflow: {workflow_type.value} with confidence {confidence:.2f}"
        )

        return WorkflowSelectionResult(
            workflow_type=workflow_type,
            confidence=confidence,
            reasoning=reasoning,
            config=config,
        )

    def _build_workflow_config(
        self,
        workflow_type: WorkflowType,
        task_type: TaskType,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        構建工作流配置

        Args:
            workflow_type: 工作流類型
            task_type: 任務類型
            context: 上下文信息

        Returns:
            工作流配置字典
        """
        config: Dict[str, Any] = {
            "workflow_type": workflow_type.value,
            "task_type": task_type.value,
        }

        # 根據工作流類型添加特定配置
        if workflow_type == WorkflowType.LANGCHAIN:
            config.update(
                {
                    "enable_memory": True,
                    "enable_tools": True,
                    "enable_rag": True,
                    "max_iterations": 10,
                }
            )
        elif workflow_type == WorkflowType.CREWAI:
            config.update(
                {
                    "enable_crew": True,
                    "max_agents": 5,
                    "collaboration_mode": "sequential",  # sequential, parallel, hierarchical
                }
            )
        elif workflow_type == WorkflowType.AUTOGEN:
            config.update(
                {
                    "enable_planning": True,
                    "max_steps": 20,
                    "planning_mode": "auto",  # auto, manual, hybrid
                }
            )
        elif workflow_type == WorkflowType.HYBRID:
            config.update(
                {
                    "primary_workflow": WorkflowType.AUTOGEN.value,
                    "secondary_workflow": WorkflowType.LANGCHAIN.value,
                    "switch_threshold": 0.7,
                }
            )

        # 合併上下文中的配置覆蓋
        if context and "workflow_config" in context:
            config.update(context["workflow_config"])

        return config
