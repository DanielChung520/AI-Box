# 代碼功能說明: AI治理報告API路由
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""AI治理報告API路由 - 提供AI治理報告生成接口、變更提案和版本歷史管理"""

from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.change_proposal import ChangeProposalCreate, ProposalStatus
from services.api.services.governance.change_proposal_service import SeaweedFSChangeProposalService
from services.api.services.governance.seaweedfs_log_service import _get_seaweedfs_storage
from services.api.services.governance.version_history_service import SeaweedFSVersionHistoryService
from services.api.services.governance_report_service import get_governance_report_service
from system.security.dependencies import get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/governance", tags=["AI Governance"])


@router.get("/report")
async def get_governance_report(
    start_time: Optional[datetime] = Query(None, description="開始時間"),
    end_time: Optional[datetime] = Query(None, description="結束時間"),
    user_id: Optional[str] = Query(None, description="用戶ID（僅管理員可用）"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取AI治理報告

    Args:
        start_time: 開始時間
        end_time: 結束時間
        user_id: 用戶ID（僅管理員可用）
        current_user: 當前認證用戶

    Returns:
        AI治理報告
    """
    try:
        # 非管理員用戶只能查詢自己的報告
        from system.security.models import Permission

        if not current_user.has_permission(Permission.ALL.value):
            user_id = current_user.user_id

        service = get_governance_report_service()
        report = service.generate_report(start_time=start_time, end_time=end_time, user_id=user_id)

        return APIResponse.success(
            data=report,
            message="AI治理報告生成成功",
        )
    except Exception as e:
        logger.error("AI治理報告生成失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"AI治理報告生成失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# 變更提案服務實例（單例模式）
_proposal_service: Optional[SeaweedFSChangeProposalService] = None
_version_history_service: Optional[SeaweedFSVersionHistoryService] = None


def get_proposal_service() -> SeaweedFSChangeProposalService:
    """獲取變更提案服務實例（單例模式）"""
    global _proposal_service
    if _proposal_service is None:
        storage = _get_seaweedfs_storage()
        _proposal_service = SeaweedFSChangeProposalService(storage)
    return _proposal_service


def get_version_history_service() -> SeaweedFSVersionHistoryService:
    """獲取版本歷史服務實例（單例模式）"""
    global _version_history_service
    if _version_history_service is None:
        storage = _get_seaweedfs_storage()
        _version_history_service = SeaweedFSVersionHistoryService(storage)
    return _version_history_service


# ==================== 變更提案 API ====================


@router.post("/proposals", status_code=status.HTTP_201_CREATED)
async def create_proposal(
    proposal_data: ChangeProposalCreate,
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    創建變更提案

    Args:
        proposal_data: 變更提案創建請求
        current_user: 當前認證用戶

    Returns:
        創建的提案ID
    """
    try:
        service = get_proposal_service()
        # 使用當前用戶ID作為提案者
        proposal_data.proposed_by = current_user.user_id
        proposal_id = await service.create_proposal(proposal_data)
        return APIResponse.success(
            data={"proposal_id": proposal_id},
            message="變更提案創建成功",
        )
    except Exception as e:
        logger.error("創建變更提案失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"創建變更提案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/proposals/{proposal_id}")
async def get_proposal(
    proposal_id: str = Path(..., description="提案ID"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取提案詳情

    Args:
        proposal_id: 提案ID
        current_user: 當前認證用戶

    Returns:
        提案詳情
    """
    try:
        service = get_proposal_service()
        proposal = await service.get_proposal(proposal_id)
        if proposal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提案 {proposal_id} 不存在",
            )
        return APIResponse.success(
            data=proposal.dict(),
            message="獲取提案詳情成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取提案詳情失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"獲取提案詳情失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/proposals/{proposal_id}/approve")
async def approve_proposal(
    proposal_id: str = Path(..., description="提案ID"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    審批提案

    Args:
        proposal_id: 提案ID
        current_user: 當前認證用戶

    Returns:
        審批結果
    """
    try:
        service = get_proposal_service()
        success = await service.approve_proposal(proposal_id, current_user.user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提案 {proposal_id} 不存在",
            )
        return APIResponse.success(
            message="提案審批成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("審批提案失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"審批提案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/proposals/{proposal_id}/reject")
async def reject_proposal(
    proposal_id: str = Path(..., description="提案ID"),
    reason: str = Body(..., embed=True, description="拒絕原因"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    拒絕提案

    Args:
        proposal_id: 提案ID
        reason: 拒絕原因
        current_user: 當前認證用戶

    Returns:
        拒絕結果
    """
    try:
        service = get_proposal_service()
        success = await service.reject_proposal(proposal_id, current_user.user_id, reason)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"提案 {proposal_id} 不存在",
            )
        return APIResponse.success(
            message="提案拒絕成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("拒絕提案失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"拒絕提案失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/proposals")
async def list_proposals(
    proposal_type: Optional[str] = Query(None, description="提案類型"),
    resource_id: Optional[str] = Query(None, description="資源ID"),
    status: Optional[ProposalStatus] = Query(None, description="提案狀態"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    列出提案列表

    Args:
        proposal_type: 提案類型（可選）
        resource_id: 資源ID（可選）
        status: 提案狀態（可選）
        limit: 返回數量限制
        current_user: 當前認證用戶

    Returns:
        提案列表
    """
    try:
        service = get_proposal_service()
        proposals = await service.list_proposals(
            proposal_type=proposal_type,
            resource_id=resource_id,
            status=status,
            limit=limit,
        )
        return APIResponse.success(
            data=[p.dict() for p in proposals],
            message="獲取提案列表成功",
        )
    except Exception as e:
        logger.error("獲取提案列表失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"獲取提案列表失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# ==================== 版本歷史 API ====================


@router.get("/versions/{resource_type}/{resource_id}")
async def get_version_history(
    resource_type: str = Path(..., description="資源類型（如 ontologies, configs）"),
    resource_id: str = Path(..., description="資源ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取版本歷史

    Args:
        resource_type: 資源類型
        resource_id: 資源ID
        limit: 返回數量限制
        current_user: 當前認證用戶

    Returns:
        版本歷史列表
    """
    try:
        service = get_version_history_service()
        versions = await service.get_version_history(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit,
        )
        return APIResponse.success(
            data=[v.dict() for v in versions],
            message="獲取版本歷史成功",
        )
    except Exception as e:
        logger.error("獲取版本歷史失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"獲取版本歷史失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/versions/{resource_type}/{resource_id}/{version}")
async def get_version(
    resource_type: str = Path(..., description="資源類型"),
    resource_id: str = Path(..., description="資源ID"),
    version: int = Path(..., ge=1, description="版本號"),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """
    獲取特定版本

    Args:
        resource_type: 資源類型
        resource_id: 資源ID
        version: 版本號
        current_user: 當前認證用戶

    Returns:
        版本歷史記錄
    """
    try:
        service = get_version_history_service()
        version_record = await service.get_version(
            resource_type=resource_type,
            resource_id=resource_id,
            version=version,
        )
        if version_record is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"版本 {version} 不存在",
            )
        return APIResponse.success(
            data=version_record.dict(),
            message="獲取版本詳情成功",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("獲取版本詳情失敗", error=str(e), exc_info=True)
        return APIResponse.error(
            message=f"獲取版本詳情失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
