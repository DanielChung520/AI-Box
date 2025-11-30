# 代碼功能說明: Agent Files API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Files API 路由 - 提供 Agent 產出物的上傳和訪問接口"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query
from fastapi import status as http_status
from fastapi.responses import JSONResponse, FileResponse

from services.api.core.response import APIResponse
from agents.services.file_service.agent_file_service import get_agent_file_service
from agents.services.file_service.models import FileType

router = APIRouter()


@router.post("/files/upload", status_code=http_status.HTTP_201_CREATED)
async def upload_agent_file(
    file: UploadFile = File(...),
    agent_id: str = Query(..., description="Agent ID"),
    task_id: str = Query(..., description="任務 ID"),
    file_type: Optional[str] = Query(None, description="文件類型（自動推斷）"),
) -> JSONResponse:
    """
    上傳 Agent 產出物文件

    Args:
        file: 上傳的文件
        agent_id: Agent ID
        task_id: 任務 ID
        file_type: 文件類型（可選，自動從文件名推斷）

    Returns:
        文件信息
    """
    try:
        file_service = get_agent_file_service()

        # 讀取文件內容
        file_content = await file.read()

        # 確定文件類型
        parsed_file_type = None
        if file_type:
            try:
                parsed_file_type = FileType(file_type.lower())
            except ValueError:
                pass  # 使用自動推斷

        # 上傳文件
        file_info = file_service.upload_agent_output(
            file_content=file_content,
            filename=file.filename or "unknown",
            agent_id=agent_id,
            task_id=task_id,
            file_type=parsed_file_type,
        )

        return APIResponse.success(
            data=file_info.model_dump(mode="json"),
            message="File uploaded successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}",
        )


@router.get(
    "/files/{agent_id}/{task_id}/{file_id}", status_code=http_status.HTTP_200_OK
)
async def get_agent_file(
    agent_id: str,
    task_id: str,
    file_id: str,
) -> FileResponse:
    """
    下載 Agent 產出物文件

    Args:
        agent_id: Agent ID
        task_id: 任務 ID
        file_id: 文件 ID

    Returns:
        文件響應
    """
    try:
        file_service = get_agent_file_service()
        file_info = file_service.get_agent_file(agent_id, task_id, file_id)

        if file_info is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"File not found: {file_id}",
            )

        return FileResponse(
            path=file_info.file_path,
            filename=file_info.filename,
            media_type="application/octet-stream",
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file: {str(e)}",
        )


@router.get("/files/{agent_id}", status_code=http_status.HTTP_200_OK)
async def list_agent_files(
    agent_id: str,
    task_id: Optional[str] = Query(None, description="任務 ID 過濾器"),
) -> JSONResponse:
    """
    列出 Agent 的文件

    Args:
        agent_id: Agent ID
        task_id: 任務 ID（可選過濾器）

    Returns:
        文件列表
    """
    try:
        file_service = get_agent_file_service()
        files = file_service.list_agent_files(agent_id, task_id)

        return APIResponse.success(
            data={
                "agent_id": agent_id,
                "task_id": task_id,
                "files": [file.model_dump(mode="json") for file in files],
                "count": len(files),
            },
            message="Files retrieved successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}",
        )
