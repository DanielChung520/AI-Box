# 代碼功能說明: P-T-A-O 資料模型定義
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""P-T-A-O 資料模型定義 — Plan-Think-Act-Observe 架構"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ThoughtTrace(BaseModel):
    """思考跡象 — 代理在規劃和思考階段的推理過程記錄

    用於記錄代理如何分析用戶指令，以及複雜度評估。
    """

    reasoning: str = Field(..., description="推理過程的詳細描述", min_length=1)
    intent_summary: str = Field(..., description="意圖摘要")
    complexity: Literal["simple", "complex"] = Field(
        default="simple",
        description="問題複雜度評估",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="記錄時間戳",
    )

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning_not_empty(cls, v: str) -> str:
        """確保 reasoning 不為空"""
        if not v or not v.strip():
            raise ValueError("reasoning 不能為空")
        return v


class Observation(BaseModel):
    """觀察結果 — 代理執行動作後的反饋和結果

    記錄動作執行的成功/失敗、耗時和返回的數據。
    """

    source: str = Field(..., description="觀察數據的來源（如 'data_agent', 'cache' 等）")
    success: bool = Field(..., description="操作是否成功")
    data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="成功時的返回數據",
    )
    error: Optional[str] = Field(
        default=None,
        description="失敗時的錯誤信息",
    )
    duration_ms: float = Field(..., description="操作耗時（毫秒）", ge=0.0)

    @field_validator("data", "error", mode="before")
    @classmethod
    def validate_data_or_error(cls, v: Any) -> Any:
        """確保 success=True 時有 data，success=False 時有 error"""
        return v

    def model_post_init(self, __context: Any) -> None:
        """後期驗證：success 和 data/error 的一致性"""
        if self.success and self.data is None:
            raise ValueError("success=True 時必須提供 data")
        if not self.success and self.error is None:
            raise ValueError("success=False 時必須提供 error")


class DecisionEntry(BaseModel):
    """決策項 — 代理在不同階段（P/T/A/O）的決策記錄

    記錄每個決策點的階段、行動和理由。
    """

    phase: Literal["plan", "think", "act", "observe"] = Field(
        ..., description="決策所在的 P-T-A-O 階段"
    )
    action: str = Field(..., description="執行的具體行動")
    rationale: str = Field(..., description="行動的理由或依據")
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="決策時間戳",
    )


class DecisionLog(BaseModel):
    """決策日誌 — 完整的決策歷史記錄

    記錄代理在整個執行過程中的所有決策，按時間順序排列。
    """

    entries: List[DecisionEntry] = Field(
        default_factory=list,
        description="決策項列表",
    )

    def add_entry(self, entry: DecisionEntry) -> None:
        """新增決策項到日誌

        Args:
            entry: 要新增的決策項
        """
        self.entries.append(entry)


class PTAOResult(BaseModel):
    """P-T-A-O 執行結果 — 完整的代理執行過程記錄

    整合思考、觀察、決策和原始結果，提供完整的執行追蹤能力。

    Attributes:
        thought: 思考跡象，記錄規劃和思考階段
        observation: 觀察結果，記錄執行和反饋
        decision_log: 決策日誌，記錄所有決策點
        raw_result: 原始執行結果
    """

    thought: ThoughtTrace = Field(..., description="思考跡象")
    observation: Observation = Field(..., description="觀察結果")
    decision_log: DecisionLog = Field(..., description="決策日誌")
    raw_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="原始執行結果",
    )

    class Config:
        """Pydantic 配置"""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }
