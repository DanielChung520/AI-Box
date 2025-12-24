# 代碼功能說明: Execution Agent API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Execution Agent API 路由"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agents.core.execution.agent import ExecutionAgent
from agents.core.execution.models import ExecutionRequest
from services.api.core.response import APIResponse

router = APIRouter()

# 初始化 Execution Agent
execution_agent = ExecutionAgent()


class ExecutionAPIRequest(BaseModel):
    """執行 API 請求模型"""

    task: str
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    plan_step_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolRegisterRequest(BaseModel):
    """工具註冊請求模型"""

    tool_name: str
    description: str
    tool_type: str = "custom"
    config: Optional[Dict[str, Any]] = None


@router.post("/agents/execution/execute", status_code=status.HTTP_200_OK)
async def execute_task(request: ExecutionAPIRequest) -> JSONResponse:
    """
    執行任務

    Args:
        request: 執行請求

    Returns:
        執行結果
    """
    try:
        # 構建 ExecutionRequest
        execution_request = ExecutionRequest(
            task=request.task,
            tool_name=request.tool_name,
            tool_args=request.tool_args,
            plan_step_id=request.plan_step_id,
            context=request.context,
            metadata=request.metadata or {},
        )

        # 執行任務
        result = execution_agent.execute(execution_request)

        return APIResponse.success(
            data=result.model_dump(mode="json"),
            message="Task executed successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Task execution failed: {str(e)}",
        )


@router.post("/agents/execution/tools/register", status_code=status.HTTP_201_CREATED)
async def register_tool(request: ToolRegisterRequest) -> JSONResponse:
    """
    註冊工具

    Args:
        request: 工具註冊請求

    Returns:
        註冊結果
    """
    try:
        # 這裡需要一個工具處理函數，暫時使用占位符
        def tool_handler(**kwargs):
            return {"success": True, "message": "Tool executed"}

        success = execution_agent.register_tool(
            name=request.tool_name,
            description=request.description,
            handler=tool_handler,
            tool_type=request.tool_type,
            config=request.config,
        )

        if success:
            return APIResponse.success(
                data={"tool_name": request.tool_name, "registered": True},
                message="Tool registered successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to register tool",
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool registration failed: {str(e)}",
        )


@router.get("/agents/execution/tools", status_code=status.HTTP_200_OK)
async def list_tools() -> JSONResponse:
    """
    列出已註冊的工具

    Returns:
        工具列表
    """
    try:
        tool_registry = execution_agent.tool_registry
        tools = tool_registry.list_tools()

        # 轉換工具對象為字典
        tools_data = []
        for tool in tools:
            tool_dict = {
                "name": tool.name,
                "description": tool.description,
                "tool_type": (
                    tool.tool_type.value
                    if hasattr(tool.tool_type, "value")
                    else str(tool.tool_type)
                ),
            }
            tools_data.append(tool_dict)

        return APIResponse.success(
            data={"tools": tools_data},
            message="Tools retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tools: {str(e)}",
        )


@router.get("/agents/execution/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Execution Agent 健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "execution_agent"},
        message="Execution Agent is healthy",
    )
