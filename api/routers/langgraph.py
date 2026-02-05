# 代碼功能說明: LangGraph 工作流 API 路由
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

"""LangGraph 工作流執行 API 路由"""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from genai.workflows.langgraph.engine import TaskExecutionEngine
from genai.workflows.langgraph.state import AIBoxState

logger = logging.getLogger(__name__)

router = APIRouter()


class LangGraphExecuteRequest(BaseModel):
    """LangGraph 工作流執行請求模型"""
    task: str = Field(..., description="任務描述")
    user_id: str = Field(..., description="用戶ID")
    session_id: Optional[str] = Field(default=None, description="會話ID")
    context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="上下文信息")
    workflow_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="工作流配置",
    )


class LangGraphStatusResponse(BaseModel):
    """LangGraph 狀態響應模型"""
    workflow_id: str
    status: str
    current_layer: str
    execution_time: float
    node_count: int
    error_count: int
    layers_executed: list[str]


class LangGraphResultResponse(BaseModel):
    """LangGraph 結果響應模型"""
    workflow_id: str
    success: bool
    final_state: Dict[str, Any]
    execution_time: float
    node_count: int
    error_count: int
    layers_executed: list[str]
    final_layer: str
    reasoning: str


# 全局執行引擎實例
_execution_engine = TaskExecutionEngine()
_active_workflows: Dict[str, Any] = {}


@router.post("/langgraph/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_langgraph_workflow(request: LangGraphExecuteRequest) -> JSONResponse:
    """
    啟動 LangGraph 工作流執行

    Args:
        request: 工作流執行請求

    Returns:
        工作流ID和初始狀態
    """
    try:
        # 生成工作流ID
        workflow_id = str(uuid.uuid4())

        # 創建初始狀態
        initial_state = AIBoxState(
            task_id=workflow_id,
            user_id=request.user_id,
            session_id=request.session_id or f"session_{request.user_id}",
            task=request.task,
            context=request.context,
            workflow_config=request.workflow_config,
        )

        # 存儲初始狀態（實際項目中應該使用資料庫或快取）
        _active_workflows[workflow_id] = {
            "state": initial_state,
            "status": "running",
            "start_time": datetime.now(),
            "user_id": request.user_id,
        }

        # 異步啟動工作流執行（使用背景任務）
        logger.info(f"Starting LangGraph workflow execution: {workflow_id}")

        # 在背景中執行工作流
        import asyncio

        asyncio.create_task(_execute_workflow_async(workflow_id, initial_state))

        return APIResponse.success(
            data={
                "workflow_id": workflow_id,
                "status": "running",
                "message": "Workflow execution started",
            },
            message="LangGraph workflow execution initiated",
        )

    except Exception as e:
        error_msg = f"LangGraph workflow execution failed to start: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


async def _execute_workflow_async(workflow_id: str, initial_state: AIBoxState) -> None:
    """異步執行工作流"""
    try:
        execution_result = await _execution_engine.execute_task(initial_state)

        # 更新工作流狀態
        _active_workflows[workflow_id].update(
            {
                "status": "completed" if execution_result.success else "failed",
                "result": {
                    "success": execution_result.success,
                    "final_state": execution_result.final_state.to_dict(),
                    "execution_time": execution_result.execution_time,
                    "node_count": execution_result.node_count,
                    "error_count": execution_result.error_count,
                    "layers_executed": execution_result.layers_executed,
                    "final_layer": execution_result.final_layer,
                    "reasoning": execution_result.reasoning,
                },
                "end_time": datetime.now(),
            }
        )

        logger.info(
            f"LangGraph workflow completed: {workflow_id}, success={execution_result.success}",
        )

    except Exception as e:
        logger.error(f"LangGraph workflow execution failed: {workflow_id}, error={e}")
        _active_workflows[workflow_id].update(
            {
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now(),
            }
        )


@router.get("/langgraph/status/{workflow_id}", status_code=status.HTTP_200_OK)
async def get_langgraph_workflow_status(workflow_id: str) -> JSONResponse:
    """
    獲取 LangGraph 工作流狀態

    Args:
        workflow_id: 工作流ID

    Returns:
        工作流狀態
    """
    try:
        if workflow_id not in _active_workflows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )

        workflow_data = _active_workflows[workflow_id]
        status_data = {
            "workflow_id": workflow_id,
            "status": workflow_data["status"],
            "start_time": workflow_data["start_time"].isoformat(),
            "user_id": workflow_data["user_id"],
        }

        if "end_time" in workflow_data:
            status_data["end_time"] = workflow_data["end_time"].isoformat()

        if "result" in workflow_data:
            result = workflow_data["result"]
            status_data.update(
                {
                    "execution_time": result["execution_time"],
                    "node_count": result["node_count"],
                    "error_count": result["error_count"],
                    "layers_executed": result["layers_executed"],
                    "final_layer": result["final_layer"],
                }
            )

        return APIResponse.success(
            data=status_data,
            message="Workflow status retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to retrieve workflow status: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


@router.get("/langgraph/results/{workflow_id}", status_code=status.HTTP_200_OK)
async def get_langgraph_workflow_results(workflow_id: str) -> JSONResponse:
    """
    獲取 LangGraph 工作流結果

    Args:
        workflow_id: 工作流ID

    Returns:
        工作流結果
    """
    try:
        if workflow_id not in _active_workflows:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow {workflow_id} not found",
            )

        workflow_data = _active_workflows[workflow_id]

        if workflow_data["status"] not in ["completed", "failed"]:
            return APIResponse.success(
                data={
                    "workflow_id": workflow_id,
                    "status": workflow_data["status"],
                    "message": "Workflow is still running",
                },
                message="Workflow execution in progress",
            )

        if "result" not in workflow_data:
            return APIResponse.error(
                message="Workflow result not available",
                data={"workflow_id": workflow_id, "status": workflow_data["status"]},
            )

        result_data = workflow_data["result"].copy()
        result_data["workflow_id"] = workflow_id

        return APIResponse.success(
            data=result_data,
            message="Workflow results retrieved successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Failed to retrieve workflow results: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e


@router.get("/langgraph/health", status_code=status.HTTP_200_OK)
async def langgraph_health_check() -> JSONResponse:
    """
    LangGraph 服務健康檢查

    Returns:
        健康狀態
    """
    return APIResponse.success(
        data={"status": "healthy", "service": "langgraph"},
        message="LangGraph service is healthy",
    )


@router.get("/langgraph/agents", status_code=status.HTTP_200_OK)
async def list_langgraph_agents() -> JSONResponse:
    """
    獲取可用 LangGraph Agent 列表

    Returns:
        Agent 列表
    """
    try:
        # 這裡可以從節點註冊表獲取可用Agent
        agents = [
            {
                "name": "semantic_analyzer",
                "description": "語義分析Agent",
                "layer": "semantic_analysis",
            },
            {
                "name": "intent_classifier",
                "description": "意圖分類Agent",
                "layer": "intent_classification",
            },
            {
                "name": "capability_matcher",
                "description": "能力匹配Agent",
                "layer": "capability_matching",
            },
            {
                "name": "resource_manager",
                "description": "資源管理Agent",
                "layer": "resource_management",
            },
            {
                "name": "policy_enforcer",
                "description": "策略執行Agent",
                "layer": "policy_enforcement",
            },
            {"name": "orchestrator", "description": "協調器Agent", "layer": "orchestration"},
            {"name": "task_executor", "description": "任務執行Agent", "layer": "execution"},
            {
                "name": "user_confirmation",
                "description": "用戶確認Agent",
                "layer": "user_interaction",
            },
            {"name": "clarification", "description": "澄清Agent", "layer": "clarification"},
            {
                "name": "simple_response",
                "description": "簡單響應Agent",
                "layer": "response_generation",
            },
            {"name": "file_processor", "description": "文件處理Agent", "layer": "file_processing"},
            {"name": "vectorizer", "description": "向量化Agent", "layer": "vectorization"},
            {"name": "kg_extractor", "description": "知識圖譜提取Agent", "layer": "kg_extraction"},
            {"name": "rag_retriever", "description": "RAG檢索Agent", "layer": "retrieval"},
            {"name": "hybrid_rag", "description": "混合RAG Agent", "layer": "hybrid_retrieval"},
            {"name": "task_manager", "description": "任務管理Agent", "layer": "task_management"},
            {
                "name": "workspace_manager",
                "description": "工作區管理Agent",
                "layer": "workspace_management",
            },
            {
                "name": "file_task_binder",
                "description": "文件任務綁定Agent",
                "layer": "file_task_binding",
            },
            {
                "name": "context_manager",
                "description": "上下文管理Agent",
                "layer": "context_management",
            },
            {
                "name": "memory_manager",
                "description": "記憶管理Agent",
                "layer": "memory_management",
            },
            {
                "name": "long_term_memory",
                "description": "長期記憶Agent",
                "layer": "long_term_memory",
            },
            {"name": "audit_logger", "description": "審計日誌Agent", "layer": "audit_logging"},
            {"name": "observer", "description": "觀察者Agent", "layer": "observation"},
            {
                "name": "performance_optimizer",
                "description": "效能優化Agent",
                "layer": "performance_optimization",
            },
            {"name": "error_handler", "description": "錯誤處理Agent", "layer": "error_handling"},
            {
                "name": "integration_tester",
                "description": "整合測試Agent",
                "layer": "integration_testing",
            },
            {
                "name": "production_readiness",
                "description": "生產就緒Agent",
                "layer": "production_readiness",
            },
        ]

        return APIResponse.success(
            data={"agents": agents, "total": len(agents)},
            message="LangGraph agents retrieved successfully",
        )

    except Exception as e:
        error_msg = f"Failed to retrieve LangGraph agents: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        ) from e
