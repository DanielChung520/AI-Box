# 代碼功能說明: 知識圖譜構建路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""知識圖譜構建路由 - 提供圖譜構建 API 端點"""

from typing import List, Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from genai.api.models.triple_models import Triple
from genai.api.services.kg_builder_service import KGBuilderService

router = APIRouter(prefix="/kg", tags=["Knowledge Graph Builder"])

# 全局服務實例（懶加載）
_service: Optional[KGBuilderService] = None


def get_service() -> KGBuilderService:
    """獲取知識圖譜構建服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = KGBuilderService()
    return _service


@router.post("/build")
async def build_kg_from_triples(triples: List[Triple]) -> JSONResponse:
    """從三元組構建圖譜"""
    service = get_service()

    try:
        result = await service.build_from_triples(triples)
        return APIResponse.success(data=result, message="知識圖譜構建成功")
    except RuntimeError as e:
        return APIResponse.error(
            message=f"知識圖譜構建失敗: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return APIResponse.error(
            message=f"知識圖譜構建失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/build/batch")
async def build_kg_from_triples_batch(triples_list: List[List[Triple]]) -> JSONResponse:
    """批量構建圖譜"""
    service = get_service()

    try:
        result = await service.build_from_triples_batch(triples_list)
        return APIResponse.success(data=result, message="批量知識圖譜構建成功")
    except Exception as e:
        return APIResponse.error(
            message=f"批量知識圖譜構建失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/update")
async def update_kg_from_triples(triples: List[Triple]) -> JSONResponse:
    """增量更新圖譜"""
    service = get_service()

    try:
        result = await service.build_from_triples(triples)
        return APIResponse.success(data=result, message="知識圖譜更新成功")
    except Exception as e:
        return APIResponse.error(
            message=f"知識圖譜更新失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
