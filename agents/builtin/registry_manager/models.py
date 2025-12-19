# 代碼功能說明: Registry Manager Agent 數據模型
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Registry Manager Agent 數據模型定義"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from agents.services.registry.models import AgentRegistryInfo


class RegistryManagerRequest(BaseModel):
    """注册管理请求模型"""

    action: str = Field(..., description="操作类型（match, discover, recommend, analyze）")
    task_description: Optional[str] = Field(None, description="任务描述（用于匹配）")
    required_capabilities: Optional[List[str]] = Field(None, description="需要的能力列表")
    agent_type: Optional[str] = Field(None, description="Agent 类型过滤器")
    category: Optional[str] = Field(None, description="Agent 分类过滤器")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


class RegistryManagerResponse(BaseModel):
    """注册管理响应模型"""

    success: bool = Field(..., description="是否成功")
    action: str = Field(..., description="执行的操作类型")
    agents: Optional[List[AgentRegistryInfo]] = Field(None, description="匹配的 Agent 列表")
    recommendations: Optional[List[Dict[str, Any]]] = Field(None, description="AI 推荐结果")
    analysis: Optional[Dict[str, Any]] = Field(None, description="分析结果")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
