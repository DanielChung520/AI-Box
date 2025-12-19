# 代碼功能說明: CrewAI 數據模型定義
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""定義 CrewAI 相關的數據模型。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class CollaborationMode(str, Enum):
    """協作模式枚舉。"""

    SEQUENTIAL = "sequential"  # 順序執行
    HIERARCHICAL = "hierarchical"  # 層級協調
    CONSENSUAL = "consensual"  # 共識協商


class AgentRole(BaseModel):
    """Agent 角色定義。"""

    role: str = Field(..., description="角色名稱")
    goal: str = Field(..., description="角色目標")
    backstory: str = Field(..., description="角色背景故事")
    tools: List[str] = Field(default_factory=list, description="工具列表")
    verbose: bool = Field(default=True, description="是否輸出詳細日誌")
    allow_delegation: bool = Field(default=False, description="是否允許委派任務")


class CrewResourceQuota(BaseModel):
    """資源配額配置。"""

    token_budget: int = Field(default=100000, ge=1000, description="Token 預算上限")
    max_iterations: int = Field(default=20, ge=1, le=100, description="最大迭代次數")
    timeout: int = Field(default=3600, ge=60, description="超時時間（秒）")


class CrewMetrics(BaseModel):
    """觀測指標。"""

    crew_id: str = Field(..., description="隊伍 ID")
    agent_count: int = Field(default=0, description="Agent 數量")
    task_count: int = Field(default=0, description="任務數量")
    token_usage: int = Field(default=0, description="Token 使用量")
    execution_time: float = Field(default=0.0, description="執行時間（秒）")
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="成功率")
    last_updated: datetime = Field(default_factory=datetime.now, description="最後更新時間")


class CrewConfig(BaseModel):
    """隊伍配置。"""

    crew_id: str = Field(..., description="隊伍 ID")
    name: str = Field(..., description="隊伍名稱")
    description: Optional[str] = Field(default=None, description="隊伍描述")
    agents: List[AgentRole] = Field(default_factory=list, description="Agent 列表")
    collaboration_mode: CollaborationMode = Field(
        default=CollaborationMode.SEQUENTIAL, description="協作模式"
    )
    resource_quota: CrewResourceQuota = Field(
        default_factory=CrewResourceQuota, description="資源配額"
    )
    created_at: datetime = Field(default_factory=datetime.now, description="創建時間")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新時間")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元數據")


@dataclass
class CrewRegistryEntry:
    """隊伍註冊表條目。"""

    crew_id: str
    config: CrewConfig
    metrics: CrewMetrics
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典。"""
        return {
            "crew_id": self.crew_id,
            "config": self.config.model_dump(),
            "metrics": self.metrics.model_dump(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
