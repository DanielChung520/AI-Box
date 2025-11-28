# 代碼功能說明: AAM 異步任務管理 API
# 創建日期: 2025-11-28 21:54 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-28 21:54 (UTC+8)

"""AAM 異步任務管理 API - 提供任務狀態查詢、結果查詢和取消功能"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, status, BackgroundTasks
from fastapi.responses import JSONResponse
import structlog

from services.api.core.response import APIResponse
from agent_process.memory.aam.async_processor import AsyncProcessor, TaskStatus
from agent_process.memory.aam.knowledge_extraction_agent import KnowledgeExtractionAgent
from agent_process.memory.aam.aam_core import AAMManager

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/aam/async", tags=["AAM Async Tasks"])

# 全局異步處理器實例（實際應用中應該使用依賴注入）
_async_processor: Optional[AsyncProcessor] = None
_knowledge_agent: Optional[KnowledgeExtractionAgent] = None


def get_async_processor() -> AsyncProcessor:
    """獲取異步處理器實例"""
    global _async_processor
    if _async_processor is None:
        _async_processor = AsyncProcessor(max_workers=4)
    return _async_processor


def get_knowledge_agent() -> KnowledgeExtractionAgent:
    """獲取知識提取 Agent 實例"""
    global _knowledge_agent
    if _knowledge_agent is None:
        # 需要 AAM 管理器實例（實際應用中應該從依賴注入獲取）
        aam_manager = AAMManager()  # 這裡應該從配置或依賴注入獲取
        _knowledge_agent = KnowledgeExtractionAgent(aam_manager)
    return _knowledge_agent


@router.post("/tasks/extract-knowledge")
async def submit_knowledge_extraction_task(
    memory_id: str,
    memory_type: Optional[str] = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
) -> JSONResponse:
    """
    提交知識提取任務

    Args:
        memory_id: 記憶 ID
        memory_type: 記憶類型（short_term/long_term）
        background_tasks: FastAPI 背景任務

    Returns:
        任務 ID
    """
    try:
        processor = get_async_processor()
        agent = get_knowledge_agent()

        from agent_process.memory.aam.models import MemoryType

        mem_type = MemoryType(memory_type) if memory_type else None

        # 定義任務函數
        async def extract_task():
            return await agent.extract_knowledge_from_memory(memory_id, mem_type)

        # 提交任務
        task_id = processor.submit_task(
            task_type="knowledge_extraction",
            task_func=lambda: extract_task(),  # 注意：這裡需要處理異步函數
            priority=1,
            metadata={"memory_id": memory_id, "memory_type": memory_type},
        )

        return APIResponse.success(
            data={"task_id": task_id},
            message="Knowledge extraction task submitted",
        )
    except Exception as e:
        logger.error("Failed to submit knowledge extraction task", error=str(e))
        return APIResponse.error(
            message=f"Failed to submit task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str) -> JSONResponse:
    """
    查詢任務狀態

    Args:
        task_id: 任務 ID

    Returns:
        任務狀態信息
    """
    try:
        processor = get_async_processor()
        task = processor.get_task(task_id)

        if task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data={
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status.value,
                "priority": task.priority,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
                "retry_count": task.retry_count,
                "error": task.error,
                "metadata": task.metadata,
            },
            message="Task status retrieved",
        )
    except Exception as e:
        logger.error("Failed to get task status", error=str(e))
        return APIResponse.error(
            message=f"Failed to get task status: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str) -> JSONResponse:
    """
    查詢任務結果

    Args:
        task_id: 任務 ID

    Returns:
        任務結果
    """
    try:
        processor = get_async_processor()
        task = processor.get_task(task_id)

        if task is None:
            return APIResponse.error(
                message="Task not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if task.status != TaskStatus.COMPLETED:
            return APIResponse.error(
                message=f"Task is not completed. Current status: {task.status.value}",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return APIResponse.success(
            data={"task_id": task.task_id, "result": task.result},
            message="Task result retrieved",
        )
    except Exception as e:
        logger.error("Failed to get task result", error=str(e))
        return APIResponse.error(
            message=f"Failed to get task result: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str) -> JSONResponse:
    """
    取消任務

    Args:
        task_id: 任務 ID

    Returns:
        取消結果
    """
    try:
        processor = get_async_processor()
        success = processor.cancel_task(task_id)

        if not success:
            return APIResponse.error(
                message="Task not found or cannot be cancelled",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        return APIResponse.success(
            data={"task_id": task_id},
            message="Task cancelled",
        )
    except Exception as e:
        logger.error("Failed to cancel task", error=str(e))
        return APIResponse.error(
            message=f"Failed to cancel task: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/tasks")
async def list_tasks(
    task_status: Optional[str] = None, task_type: Optional[str] = None
) -> JSONResponse:
    """
    列出任務

    Args:
        task_status: 任務狀態過濾
        task_type: 任務類型過濾

    Returns:
        任務列表
    """
    try:
        processor = get_async_processor()

        task_status_enum = TaskStatus(task_status) if task_status else None
        tasks = processor.list_tasks(status=task_status_enum, task_type=task_type)

        task_list = [
            {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status.value,
                "priority": task.priority,
                "created_at": task.created_at.isoformat(),
                "started_at": task.started_at.isoformat() if task.started_at else None,
                "completed_at": task.completed_at.isoformat()
                if task.completed_at
                else None,
                "retry_count": task.retry_count,
                "error": task.error,
            }
            for task in tasks
        ]

        return APIResponse.success(
            data={"tasks": task_list, "count": len(task_list)},
            message="Tasks retrieved",
        )
    except Exception as e:
        logger.error("Failed to list tasks", error=str(e))
        return APIResponse.error(
            message=f"Failed to list tasks: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
