# 代碼功能說明: NER 命名實體識別路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""NER 命名實體識別路由 - 提供實體識別 API 端點"""

from typing import Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from services.api.core.response import APIResponse
from services.api.services.ner_service import NERService
from services.api.models.ner_models import (
    NERRequest,
    NERResponse,
    NERBatchRequest,
    NERBatchResponse,
)

router = APIRouter(prefix="/text-analysis", tags=["NER"])

# 全局服務實例（懶加載）
_service: Optional[NERService] = None


def get_service() -> NERService:
    """獲取 NER 服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = NERService()
    return _service


@router.post("/ner")
async def extract_entities(request: NERRequest) -> JSONResponse:
    """單文本實體識別"""
    service = get_service()

    try:
        entities = await service.extract_entities(request.text, request.model_type)
        model_used = request.model_type or service.model_type

        response = NERResponse(
            entities=entities,
            text=request.text,
            model_used=model_used,
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"實體識別失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/ner/batch")
async def extract_entities_batch(request: NERBatchRequest) -> JSONResponse:
    """批量實體識別"""
    service = get_service()

    try:
        results = await service.extract_entities_batch(
            request.texts, request.model_type
        )
        model_used = request.model_type or service.model_type

        response_list = []
        for text, entities in zip(request.texts, results):
            response_list.append(
                NERResponse(
                    entities=entities,
                    text=text,
                    model_used=model_used,
                )
            )

        response = NERBatchResponse(
            results=response_list,
            total=len(request.texts),
            processed=len([r for r in results if r]),
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"批量實體識別失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
