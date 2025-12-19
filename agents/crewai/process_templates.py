# 代碼功能說明: Process 流程模板配置
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""定義流程模板配置和切換邏輯。"""

from typing import Any, Dict, Optional

from agents.crewai.models import CollaborationMode


class ProcessTemplate:
    """流程模板配置。"""

    def __init__(
        self,
        mode: CollaborationMode,
        config: Dict[str, Any],
    ):
        """
        初始化流程模板。

        Args:
            mode: 協作模式
            config: 配置參數
        """
        self.mode = mode
        self.config = config

    def get_config(self) -> Dict[str, Any]:
        """獲取配置。"""
        return self.config.copy()


# 預設流程模板配置
SEQUENTIAL_TEMPLATE = ProcessTemplate(
    mode=CollaborationMode.SEQUENTIAL,
    config={
        "sequential": True,
        "verbose": True,
        "max_iter": 20,
        "memory": True,
        "process": "sequential",
    },
)

HIERARCHICAL_TEMPLATE = ProcessTemplate(
    mode=CollaborationMode.HIERARCHICAL,
    config={
        "sequential": False,
        "verbose": True,
        "max_iter": 20,
        "memory": True,
        "process": "hierarchical",
        "manager_llm": None,  # 將由 LLM Adapter 填充
    },
)

CONSENSUAL_TEMPLATE = ProcessTemplate(
    mode=CollaborationMode.CONSENSUAL,
    config={
        "sequential": False,
        "verbose": True,
        "max_iter": 20,
        "memory": True,
        "process": "consensual",
        "consensus_threshold": 0.7,  # 共識閾值
    },
)


def get_process_template(mode: CollaborationMode) -> ProcessTemplate:
    """
    獲取流程模板。

    Args:
        mode: 協作模式

    Returns:
        流程模板
    """
    templates = {
        CollaborationMode.SEQUENTIAL: SEQUENTIAL_TEMPLATE,
        CollaborationMode.HIERARCHICAL: HIERARCHICAL_TEMPLATE,
        CollaborationMode.CONSENSUAL: CONSENSUAL_TEMPLATE,
    }
    return templates.get(mode, SEQUENTIAL_TEMPLATE)


def should_switch_process(
    current_mode: CollaborationMode,
    task_complexity: float,
    agent_count: int,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[CollaborationMode]:
    """
    判斷是否應該切換流程模式。

    Args:
        current_mode: 當前協作模式
        task_complexity: 任務複雜度（0-100）
        agent_count: Agent 數量
        context: 上下文信息

    Returns:
        建議的新模式，如果不需要切換則返回 None
    """
    # 如果任務複雜度很高且 Agent 數量多，建議使用共識模式
    if task_complexity > 80 and agent_count >= 3:
        if current_mode != CollaborationMode.CONSENSUAL:
            return CollaborationMode.CONSENSUAL

    # 如果任務需要明確的層級管理，建議使用層級模式
    if context and context.get("requires_hierarchy", False):
        if current_mode != CollaborationMode.HIERARCHICAL:
            return CollaborationMode.HIERARCHICAL

    # 如果任務簡單且 Agent 數量少，建議使用順序模式
    if task_complexity < 50 and agent_count <= 2:
        if current_mode != CollaborationMode.SEQUENTIAL:
            return CollaborationMode.SEQUENTIAL

    return None
