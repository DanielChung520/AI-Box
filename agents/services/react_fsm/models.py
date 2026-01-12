# 代碼功能說明: ReAct FSM 數據模型
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""ReAct FSM 數據模型定義

符合 GRO 規範的 ReAct FSM 模型。
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.services.state_store.models import ReactState, ReactStateType


class ReactResult(BaseModel):
    """ReAct 執行結果"""

    react_id: str = Field(..., description="ReAct session ID")
    success: bool = Field(..., description="是否成功")
    final_state: ReactStateType = Field(..., description="最終狀態")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    total_iterations: int = Field(..., description="總迭代次數", ge=0)
    states: List[ReactState] = Field(default_factory=list, description="狀態歷史")
