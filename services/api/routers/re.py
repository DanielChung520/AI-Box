# 代碼功能說明: RE 關係抽取路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RE 關係抽取路由 - 提供關係抽取 API 端點"""

from typing import Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from services.api.core.response import APIResponse
from services.api.services.re_service import REService
from services.api.models.re_models import (
    RERequest,
    REResponse,
    REBatchRequest,
    REBatchResponse,
)

router = APIRouter(prefix="/text-analysis", tags=["RE"])

# 全局服務實例（懶加載）
_service: Optional[REService] = None


def get_service() -> REService:
    """獲取 RE 服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = REService()
    return _service


@router.post("/re")
async def extract_relations(request: RERequest) -> JSONResponse:
    """關係抽取"""
    service = get_service()

    try:
        relations = await service.extract_relations(
            request.text, request.entities, request.model_type
        )
        model_used = request.model_type or service.model_type

        response = REResponse(
            relations=relations,
            text=request.text,
            model_used=model_used,
        )

        return APIResponse.success(data=response.model_dump())
    except RuntimeError as e:
        return APIResponse.error(
            message=f"關係抽取失敗: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return APIResponse.error(
            message=f"關係抽取失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/re/from-entities")
async def extract_relations_from_entities(request: RERequest) -> JSONResponse:
    """基於預先識別實體的關係抽取"""
    if not request.entities:
        return APIResponse.error(
            message="請提供實體列表",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    service = get_service()

    try:
        relations = await service.extract_relations(
            request.text, request.entities, request.model_type
        )
        model_used = request.model_type or service.model_type

        response = REResponse(
            relations=relations,
            text=request.text,
            model_used=model_used,
        )

        return APIResponse.success(data=response.model_dump())
    except RuntimeError as e:
        return APIResponse.error(
            message=f"關係抽取失敗: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return APIResponse.error(
            message=f"關係抽取失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/re/batch")
async def extract_relations_batch(request: REBatchRequest) -> JSONResponse:
    """批量關係抽取"""
    service = get_service()

    try:
        results = await service.extract_relations_batch(
            request.texts, request.model_type
        )
        model_used = request.model_type or service.model_type

        response_list = []
        for text, relations in zip(request.texts, results):
            response_list.append(
                REResponse(
                    relations=relations,
                    text=text,
                    model_used=model_used,
                )
            )

        response = REBatchResponse(
            results=response_list,
            total=len(request.texts),
            processed=len([r for r in results if r]),
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"批量關係抽取失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
