# 代碼功能說明: AutoGen Agent 角色定義
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""定義 AutoGen Agent 角色：規劃、執行、評估。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AgentRole:
    """Agent 角色定義。"""

    name: str
    description: str
    system_message: str
    capabilities: List[str]
    max_consecutive_auto_reply: int = 10
    human_input_mode: str = "NEVER"  # NEVER, TERMINATE, ALWAYS
    code_execution_config: Optional[Dict[str, Any]] = None


class PlanningAgentRole(AgentRole):
    """規劃 Agent 角色。"""

    def __init__(self):
        super().__init__(
            name="planner",
            description="負責生成多步驟執行計劃，分析任務需求並制定詳細的執行方案",
            system_message="""你是一個專業的任務規劃專家。你的職責是：
1. 分析用戶任務需求，識別關鍵步驟和依賴關係
2. 生成結構化的執行計劃，包含清晰的步驟序列
3. 評估計劃的可行性和資源需求
4. 根據執行反饋動態調整計劃

請確保你的計劃：
- 步驟清晰、可執行
- 考慮資源限制和時間約束
- 包含必要的驗證和檢查點
- 提供失敗處理策略""",
            capabilities=[
                "任務分析",
                "計劃生成",
                "資源評估",
                "計劃優化",
            ],
            max_consecutive_auto_reply=5,
        )


class ExecutionAgentRole(AgentRole):
    """執行 Agent 角色。"""

    def __init__(self):
        super().__init__(
            name="executor",
            description="負責執行具體的任務步驟，調用工具完成實際操作",
            system_message="""你是一個高效的任務執行專家。你的職責是：
1. 按照計劃執行具體的任務步驟
2. 調用適當的工具完成操作
3. 報告執行結果和遇到的問題
4. 在執行失敗時提供詳細的錯誤信息

請確保你的執行：
- 嚴格遵循計劃步驟
- 正確使用提供的工具
- 及時報告進度和問題
- 提供可驗證的執行結果""",
            capabilities=[
                "步驟執行",
                "工具調用",
                "結果驗證",
                "錯誤處理",
            ],
            max_consecutive_auto_reply=10,
        )


class EvaluationAgentRole(AgentRole):
    """評估 Agent 角色。"""

    def __init__(self):
        super().__init__(
            name="evaluator",
            description="負責評估執行結果，判斷任務完成度和質量",
            system_message="""你是一個嚴謹的任務評估專家。你的職責是：
1. 評估執行結果是否符合預期目標
2. 檢查執行過程中的問題和改進點
3. 判斷任務是否完成或需要重試
4. 提供改進建議和優化方向

請確保你的評估：
- 客觀、準確、全面
- 基於明確的評估標準
- 提供具體的改進建議
- 識別需要重試的步驟""",
            capabilities=[
                "結果評估",
                "質量檢查",
                "問題識別",
                "改進建議",
            ],
            max_consecutive_auto_reply=5,
        )


def get_default_agent_roles() -> Dict[str, AgentRole]:
    """
    獲取默認的 Agent 角色定義。

    Returns:
        Agent 角色字典，key 為角色名稱
    """
    return {
        "planner": PlanningAgentRole(),
        "executor": ExecutionAgentRole(),
        "evaluator": EvaluationAgentRole(),
    }
