# 代碼功能說明: Orchestrator Manager Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Orchestrator Manager Agent 數據模型定義"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class OrchestratorManagerRequest(BaseModel):
    """协调管理请求模型"""

    action: str = Field(
        ..., description="操作类型（route, balance_load, coordinate, analyze）"
    )
    task_id: Optional[str] = Field(None, description="任务 ID")
    task_description: Optional[str] = Field(None, description="任务描述")
    task_type: Optional[str] = Field(None, description="任务类型")
    required_capabilities: Optional[List[str]] = Field(None, description="需要的能力列表")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class TaskRoutingDecision(BaseModel):
    """任务路由决策模型"""

    agent_id: str = Field(..., description="选中的 Agent ID")
    agent_name: str = Field(..., description="Agent 名称")
    confidence: float = Field(..., description="置信度（0-1）")
    reasoning: str = Field(..., description="决策理由")
    alternatives: Optional[List[Dict[str, Any]]] = Field(
        None, description="备选 Agent 列表"
    )


class OrchestratorManagerResponse(BaseModel):
    """协调管理响应模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="执行的操作类型")
    routing_decision: Optional[TaskRoutingDecision] = Field(None, description="路由决策结果")
    load_balance_result: Optional[Dict[str, Any]] = Field(None, description="负载均衡结果")
    coordination_result: Optional[Dict[str, Any]] = Field(None, description="协调结果")
    analysis: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
