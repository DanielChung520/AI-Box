# 代碼功能說明: 模組化文檔 API 路由
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""模組化文檔 API 路由 - 實現主從架構文檔管理"""

from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.modular_document import (
    ModularDocumentAddSubDocumentRequest,
    ModularDocumentCreate,
    ModularDocumentRemoveSubDocumentRequest,
    ModularDocumentUpdate,
)
from services.api.services.file_metadata_service import FileMetadataService
from services.api.services.modular_document_service import ModularDocumentService
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/modular-documents", tags=["Modular Documents"])

_modular_doc_service: Optional[ModularDocumentService] = None
_metadata_service: Optional[FileMetadataService] = None


def get_modular_document_service() -> ModularDocumentService:
    """獲取模組化文檔服務實例"""
    global _modular_doc_service
    if _modular_doc_service is None:
        _modular_doc_service = ModularDocumentService()
    return _modular_doc_service


def get_metadata_service() -> FileMetadataService:
    """獲取文件元數據服務實例"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service


@router.post("", status_code=status.HTTP_201_CREATED)
def create_modular_document(
    create_request: ModularDocumentCreate,
    service: ModularDocumentService = Depends(get_modular_document_service),
    metadata_service: FileMetadataService = Depends(get_metadata_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    創建模組化文檔

    Args:
        create_request: 創建請求
        service: 模組化文檔服務
        metadata_service: 文件元數據服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        創建的模組化文檔
    """
    try:
        # 驗證主文檔文件是否存在
        master_file = metadata_service.get(create_request.master_file_id)
        if master_file is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Master file not found: {create_request.master_file_id}",
            )

        # 驗證所有子文檔文件是否存在
        existing_file_ids = {sub.sub_file_id for sub in create_request.sub_documents}
        for sub_file_id in existing_file_ids:
            sub_file = metadata_service.get(sub_file_id)
            if sub_file is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Sub-document file not found: {sub_file_id}",
                )

        # 創建模組化文檔
        modular_doc = service.create(create_request)

        # 驗證引用（檢查循環引用）
        cycle = service.check_circular_reference(modular_doc.doc_id)
        if cycle:
            # 如果檢測到循環，刪除剛創建的文檔並返回錯誤
            service.delete(modular_doc.doc_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Circular reference detected: {' -> '.join(cycle)}",
            )

        logger.info(
            "Modular document created",
            doc_id=modular_doc.doc_id,
            master_file_id=modular_doc.master_file_id,
            user_id=user.id,
            tenant_id=tenant_id,
        )

        return APIResponse.success(
            data=modular_doc.model_dump(mode="json"),
            message="Modular document created successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create modular document: {e}", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create modular document: {str(e)}",
        )


@router.get("/{doc_id}")
def get_modular_document(
    doc_id: str,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    獲取模組化文檔

    Args:
        doc_id: 模組化文檔 ID
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        模組化文檔
    """
    modular_doc = service.get(doc_id)
    if modular_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found: {doc_id}",
        )

    return APIResponse.success(data=modular_doc.model_dump(mode="json"))


@router.get("/master-file/{master_file_id}")
def get_modular_document_by_master_file(
    master_file_id: str,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    根據主文檔文件 ID 獲取模組化文檔

    Args:
        master_file_id: 主文檔文件 ID
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        模組化文檔
    """
    modular_doc = service.get_by_master_file_id(master_file_id)
    if modular_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found for master file: {master_file_id}",
        )

    return APIResponse.success(data=modular_doc.model_dump(mode="json"))


@router.put("/{doc_id}")
def update_modular_document(
    doc_id: str,
    update: ModularDocumentUpdate,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    更新模組化文檔

    Args:
        doc_id: 模組化文檔 ID
        update: 更新請求
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        更新後的模組化文檔
    """
    modular_doc = service.update(doc_id, update)
    if modular_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found: {doc_id}",
        )

    logger.info(
        "Modular document updated",
        doc_id=doc_id,
        user_id=user.id,
        tenant_id=tenant_id,
    )

    return APIResponse.success(
        data=modular_doc.model_dump(mode="json"),
        message="Modular document updated successfully",
    )


@router.post(
    "/{doc_id}/sub-documents",
    status_code=status.HTTP_201_CREATED,
)
def add_sub_document(
    doc_id: str,
    add_request: ModularDocumentAddSubDocumentRequest,
    service: ModularDocumentService = Depends(get_modular_document_service),
    metadata_service: FileMetadataService = Depends(get_metadata_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    添加分文檔引用

    Args:
        doc_id: 模組化文檔 ID
        add_request: 添加分文檔請求
        service: 模組化文檔服務
        metadata_service: 文件元數據服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        更新後的模組化文檔
    """
    # 驗證子文檔文件是否存在
    sub_file = metadata_service.get(add_request.sub_file_id)
    if sub_file is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sub-document file not found: {add_request.sub_file_id}",
        )

    modular_doc = service.add_sub_document(doc_id, add_request)
    if modular_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found: {doc_id}",
        )

    logger.info(
        "Sub-document added to modular document",
        doc_id=doc_id,
        sub_file_id=add_request.sub_file_id,
        user_id=user.id,
        tenant_id=tenant_id,
    )

    return APIResponse.success(
        data=modular_doc.model_dump(mode="json"),
        message="Sub-document added successfully",
    )


@router.post(
    "/{doc_id}/sub-documents/remove",
)
def remove_sub_document(
    doc_id: str,
    remove_request: ModularDocumentRemoveSubDocumentRequest,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    移除分文檔引用

    Args:
        doc_id: 模組化文檔 ID
        remove_request: 移除分文檔請求
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        更新後的模組化文檔
    """
    modular_doc = service.remove_sub_document(doc_id, remove_request)
    if modular_doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found: {doc_id}",
        )

    logger.info(
        "Sub-document removed from modular document",
        doc_id=doc_id,
        sub_file_id=remove_request.sub_file_id,
        user_id=user.id,
        tenant_id=tenant_id,
    )

    return APIResponse.success(
        data=modular_doc.model_dump(mode="json"),
        message="Sub-document removed successfully",
    )


@router.get("/task/{task_id}/list")
def list_modular_documents_by_task(
    task_id: str,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    根據任務 ID 列出所有模組化文檔

    Args:
        task_id: 任務 ID
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        模組化文檔列表
    """
    modular_docs = service.list_by_task_id(task_id)
    return APIResponse.success(
        data=[doc.model_dump(mode="json") for doc in modular_docs],
    )


@router.delete("/{doc_id}", status_code=status.HTTP_200_OK)
def delete_modular_document(
    doc_id: str,
    service: ModularDocumentService = Depends(get_modular_document_service),
    user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
) -> JSONResponse:
    """
    刪除模組化文檔

    Args:
        doc_id: 模組化文檔 ID
        service: 模組化文檔服務
        user: 當前用戶
        tenant_id: 租戶 ID

    Returns:
        刪除結果
    """
    success = service.delete(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modular document not found: {doc_id}",
        )

    logger.info(
        "Modular document deleted",
        doc_id=doc_id,
        user_id=user.id,
        tenant_id=tenant_id,
    )

    return APIResponse.success(
        data={"deleted": True},
        message="Modular document deleted successfully",
    )
