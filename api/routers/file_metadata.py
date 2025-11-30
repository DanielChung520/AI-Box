# 代碼功能說明: 文件元數據路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""文件元數據路由 - 提供元數據查詢、更新和搜索功能"""

from typing import Optional, List
from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.services.file_metadata_service import FileMetadataService
from services.api.models.file_metadata import FileMetadataUpdate

router = APIRouter(prefix="/files", tags=["File Metadata"])

# 全局服務實例（懶加載）
_service: Optional[FileMetadataService] = None


def get_service() -> FileMetadataService:
    """獲取元數據服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = FileMetadataService()
    return _service


@router.get("/{file_id}/metadata")
async def get_file_metadata(file_id: str) -> JSONResponse:
    """查詢單個文件元數據"""
    service = get_service()
    metadata = service.get(file_id)

    if metadata is None:
        return APIResponse.error(
            message="文件元數據不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return APIResponse.success(data=metadata.model_dump(mode="json"))


@router.get("/metadata")
async def list_file_metadata(
    file_type: Optional[str] = Query(None, description="文件類型篩選"),
    user_id: Optional[str] = Query(None, description="用戶 ID 篩選"),
    tags: Optional[List[str]] = Query(None, description="標籤篩選"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
    offset: int = Query(0, ge=0, description="偏移量"),
    sort_by: str = Query("upload_time", description="排序字段"),
    sort_order: str = Query("desc", description="排序順序（asc/desc）"),
) -> JSONResponse:
    """查詢文件元數據列表"""
    service = get_service()
    results = service.list(
        file_type=file_type,
        user_id=user_id,
        tags=tags,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return APIResponse.success(
        data={
            "files": [m.model_dump(mode="json") for m in results],
            "total": len(results),
            "limit": limit,
            "offset": offset,
        }
    )


@router.put("/{file_id}/metadata")
async def update_file_metadata(
    file_id: str, update: FileMetadataUpdate
) -> JSONResponse:
    """更新文件元數據"""
    service = get_service()
    metadata = service.update(file_id, update)

    if metadata is None:
        return APIResponse.error(
            message="文件元數據不存在",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    return APIResponse.success(data=metadata.model_dump(mode="json"), message="元數據更新成功")


@router.post("/metadata/search")
async def search_file_metadata(
    query: str = Query(..., description="搜索關鍵字"),
    limit: int = Query(100, ge=1, le=1000, description="返回數量限制"),
) -> JSONResponse:
    """全文搜索文件元數據"""
    service = get_service()
    results = service.search(query=query, limit=limit)

    return APIResponse.success(
        data={
            "files": [m.model_dump(mode="json") for m in results],
            "total": len(results),
            "query": query,
        }
    )
