# 代碼功能說明: Document Editing Agent v2.0 API 路由
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11 15:44:36 (UTC+8)

"""Document Editing Agent v2.0 API 路由

提供文件創建、編輯、刪除、Draft State、Commit & Rollback 等 API 接口。
"""

from typing import Any, Dict, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from agents.builtin.document_editing_v2.agent import DocumentEditingAgentV2
from agents.builtin.document_editing_v2.models import PatchResponse
from agents.core.editing_v2.workspace_integration import WorkspaceIntegration
from agents.services.protocol.base import AgentServiceRequest
from api.core.response import APIResponse
from services.api.services.file_metadata_service import get_metadata_service
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/document-editing-agent/v2", tags=["Document Editing Agent v2.0"])

# 全局服務實例
_workspace_integration: Optional[WorkspaceIntegration] = None
_agent: Optional[DocumentEditingAgentV2] = None


def get_workspace_integration() -> WorkspaceIntegration:
    """獲取 WorkspaceIntegration 服務實例（單例模式）"""
    global _workspace_integration
    if _workspace_integration is None:
        _workspace_integration = WorkspaceIntegration()
    return _workspace_integration


def get_agent() -> DocumentEditingAgentV2:
    """獲取 DocumentEditingAgentV2 實例（單例模式）"""
    global _agent
    if _agent is None:
        _agent = DocumentEditingAgentV2()
    return _agent


# ============================================================================
# Request/Response Models
# ============================================================================


class FileCreateRequest(BaseModel):
    """文件創建請求模型"""

    file_name: str = Field(..., description="文件名")
    task_id: str = Field(..., description="任務 ID")
    content: str = Field(..., description="文件內容")
    format: str = Field("markdown", description="文件格式（markdown, excel, pdf）")


class FileCreateResponse(BaseModel):
    """文件創建響應模型"""

    file_id: str = Field(..., description="文件 ID")
    file_path: str = Field(..., description="文件路徑")
    task_id: str = Field(..., description="任務 ID")
    folder_id: str = Field(..., description="資料夾 ID")


class FileEditRequest(BaseModel):
    """文件編輯請求模型"""

    document_context: Dict[str, Any] = Field(..., description="文檔上下文")
    edit_intent: Dict[str, Any] = Field(..., description="編輯意圖 DSL")


class FileEditResponse(BaseModel):
    """文件編輯響應模型"""

    patch_id: str = Field(..., description="Patch ID")
    patch: Dict[str, Any] = Field(..., description="Patch 響應")
    preview: Optional[str] = Field(None, description="預覽內容")


class DraftStateSaveRequest(BaseModel):
    """Draft State 保存請求模型"""

    doc_id: str = Field(..., description="文檔 ID")
    content: str = Field(..., description="草稿內容")
    patches: Optional[list] = Field(None, description="已應用的 Patches")


class DraftStateResponse(BaseModel):
    """Draft State 響應模型"""

    doc_id: str = Field(..., description="文檔 ID")
    content: Optional[str] = Field(None, description="草稿內容")
    patches: Optional[list] = Field(None, description="已應用的 Patches")


class CommitRequest(BaseModel):
    """Commit 請求模型"""

    doc_id: str = Field(..., description="文檔 ID")
    base_version_id: Optional[str] = Field(None, description="基礎版本 ID")
    summary: Optional[str] = Field(None, description="變更摘要")
    content: str = Field(..., description="最終合併後的完整內容")


class CommitResponse(BaseModel):
    """Commit 響應模型"""

    new_version_id: str = Field(..., description="新版本 ID")
    timestamp: str = Field(..., description="提交時間")


class RollbackRequest(BaseModel):
    """Rollback 請求模型"""

    doc_id: str = Field(..., description="文檔 ID")
    target_version_id: str = Field(..., description="目標版本 ID")


class RollbackResponse(BaseModel):
    """Rollback 響應模型"""

    rolled_back_to_version_id: str = Field(..., description="回滾到的版本 ID")
    timestamp: str = Field(..., description="回滾時間")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/files", status_code=status.HTTP_201_CREATED)
async def create_file(
    body: FileCreateRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建文件（在任務工作區下）

    在指定的任務工作區中創建新文件。
    """
    try:
        workspace_integration = get_workspace_integration()

        # 創建文件
        file_metadata = workspace_integration.create_file(
            task_id=body.task_id,
            user_id=current_user.user_id,
            file_name=body.file_name,
            content=body.content,
            file_format=body.format,
            tenant_id=tenant_id,
        )

        response = FileCreateResponse(
            file_id=file_metadata.file_id,
            file_path=file_metadata.storage_path or "",
            task_id=file_metadata.task_id,
            folder_id=file_metadata.folder_id or "",
        )

        return APIResponse.success(data=response.model_dump())

    except Exception as e:
        logger.error("創建文件失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"創建文件失敗: {str(e)}",
        )


@router.post("/edit", status_code=status.HTTP_200_OK)
async def edit_file(
    body: FileEditRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """編輯文件

    使用 Intent DSL 對文件進行結構化編輯。
    """
    try:
        agent = get_agent()

        # 構建 Agent 請求
        task_id = str(uuid4())
        request = AgentServiceRequest(
            task_id=task_id,
            task_data={
                "document_context": body.document_context,
                "edit_intent": body.edit_intent,
            },
            metadata={"user_id": current_user.user_id, "tenant_id": tenant_id},
        )

        # 執行編輯
        response = await agent.execute(request)

        if response.status == "error":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.error or "編輯失敗",
            )

        # 解析響應
        result = response.result
        if result is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="編輯響應為空",
            )

        patch_response = PatchResponse(**result)
        edit_response = FileEditResponse(
            patch_id=patch_response.patch_id,
            patch=result,
            preview=patch_response.preview,
        )

        return APIResponse.success(data=edit_response.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("編輯文件失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"編輯文件失敗: {str(e)}",
        )


@router.delete("/files/{file_id}", status_code=status.HTTP_200_OK)
async def delete_file(
    file_id: str,
    task_id: Optional[str] = None,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除文件

    刪除指定文件（軟刪除或物理刪除）。
    """
    try:
        workspace_integration = get_workspace_integration()

        # 權限檢查：確保用戶有權限刪除該文件
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(file_id)
        if file_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在",
            )

        # 簡化權限檢查：只檢查是否為文件所有者
        if file_metadata.user_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="無權限刪除該文件",
            )

        # 刪除文件
        success = workspace_integration.delete_file(file_id, task_id=task_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="刪除文件失敗",
            )

        return APIResponse.success(data={"file_id": file_id, "deleted": True})

    except HTTPException:
        raise
    except Exception as e:
        logger.error("刪除文件失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"刪除文件失敗: {str(e)}",
        )


# ============================================================================
# Draft State API（簡化版）
# ============================================================================

# 簡化實現：使用內存存儲（生產環境應使用數據庫或緩存）
_draft_states: Dict[str, DraftStateResponse] = {}


@router.post("/draft", status_code=status.HTTP_200_OK)
async def save_draft_state(
    body: DraftStateSaveRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """保存 Draft State

    保存文件的草稿狀態（簡化版，使用內存存儲）。
    """
    try:
        draft_state = DraftStateResponse(
            doc_id=body.doc_id,
            content=body.content,
            patches=body.patches,
        )

        # 簡化實現：使用內存存儲
        _draft_states[body.doc_id] = draft_state

        logger.info("Draft State 已保存", doc_id=body.doc_id, user_id=current_user.user_id)

        return APIResponse.success(data=draft_state.model_dump())

    except Exception as e:
        logger.error("保存 Draft State 失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"保存 Draft State 失敗: {str(e)}",
        )


@router.get("/draft/{doc_id}", status_code=status.HTTP_200_OK)
async def get_draft_state(
    doc_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """讀取 Draft State

    讀取文件的草稿狀態（簡化版，使用內存存儲）。
    """
    try:
        # 簡化實現：從內存存儲讀取
        draft_state = _draft_states.get(doc_id)

        if draft_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft State 不存在",
            )

        return APIResponse.success(data=draft_state.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("讀取 Draft State 失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"讀取 Draft State 失敗: {str(e)}",
        )


# ============================================================================
# Commit & Rollback API（簡化版）
# ============================================================================

# 簡化實現：使用內存存儲版本信息（生產環境應使用數據庫）
_versions: Dict[str, list] = {}  # {doc_id: [version1, version2, ...]}


@router.post("/commit", status_code=status.HTTP_200_OK)
async def commit_changes(
    body: CommitRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """提交變更

    將 Draft 內容寫入主存儲，創建版本快照（簡化版）。
    """
    try:
        get_workspace_integration()

        # 獲取 Draft State
        draft_state = _draft_states.get(body.doc_id)
        if draft_state is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Draft State 不存在",
            )

        # 獲取文件元數據
        metadata_service = get_metadata_service()
        # 從 doc_id 中提取 file_id（簡化實現，假設 doc_id = file_id）
        file_metadata = metadata_service.get(body.doc_id)
        if file_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在",
            )

        # 寫入文件內容
        if file_metadata.storage_path:
            from pathlib import Path

            file_path = Path(file_metadata.storage_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(body.content, encoding="utf-8")

        # 創建版本快照（簡化實現）
        new_version_id = str(uuid4())
        from datetime import datetime

        version_info = {
            "version_id": new_version_id,
            "doc_id": body.doc_id,
            "content": body.content,
            "summary": body.summary,
            "base_version_id": body.base_version_id,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": current_user.user_id,
        }

        if body.doc_id not in _versions:
            _versions[body.doc_id] = []
        _versions[body.doc_id].append(version_info)

        # 清除 Draft State
        _draft_states.pop(body.doc_id, None)

        response = CommitResponse(
            new_version_id=new_version_id,
            timestamp=version_info["created_at"],
        )

        logger.info("變更已提交", doc_id=body.doc_id, version_id=new_version_id)

        return APIResponse.success(data=response.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("提交變更失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交變更失敗: {str(e)}",
        )


@router.post("/rollback", status_code=status.HTTP_200_OK)
async def rollback_version(
    body: RollbackRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """回滾版本

    回滾到指定版本，恢復文件內容（簡化版）。
    """
    try:
        # 獲取版本列表
        versions = _versions.get(body.doc_id, [])
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="版本歷史不存在",
            )

        # 查找目標版本
        target_version = None
        for version in versions:
            if version["version_id"] == body.target_version_id:
                target_version = version
                break

        if target_version is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目標版本不存在",
            )

        # 獲取文件元數據
        metadata_service = get_metadata_service()
        file_metadata = metadata_service.get(body.doc_id)
        if file_metadata is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在",
            )

        # 恢復文件內容
        if file_metadata.storage_path:
            from pathlib import Path

            file_path = Path(file_metadata.storage_path)
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(target_version["content"], encoding="utf-8")

        response = RollbackResponse(
            rolled_back_to_version_id=body.target_version_id,
            timestamp=target_version["created_at"],
        )

        logger.info(
            "版本已回滾",
            doc_id=body.doc_id,
            version_id=body.target_version_id,
        )

        return APIResponse.success(data=response.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error("回滾版本失敗", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"回滾版本失敗: {str(e)}",
        )
