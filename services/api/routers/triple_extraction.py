# 代碼功能說明: 三元組提取路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""三元組提取路由 - 提供三元組提取 API 端點"""

from typing import Optional
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from services.api.core.response import APIResponse
from services.api.services.triple_extraction_service import TripleExtractionService
from services.api.models.triple_models import (
    TripleExtractionRequest,
    TripleExtractionResponse,
    TripleBatchRequest,
    TripleBatchResponse,
)

router = APIRouter(prefix="/text-analysis", tags=["Triple Extraction"])

# 全局服務實例（懶加載）
_service: Optional[TripleExtractionService] = None


def get_service() -> TripleExtractionService:
    """獲取三元組提取服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = TripleExtractionService()
    return _service


@router.post("/triples")
async def extract_triples(request: TripleExtractionRequest) -> JSONResponse:
    """三元組提取"""
    service = get_service()

    try:
        triples = await service.extract_triples(
            request.text, request.entities, request.enable_ner
        )

        # 統計信息
        entities_count = len(request.entities) if request.entities else 0
        relations_count = len(set(t.relation.type for t in triples))

        response = TripleExtractionResponse(
            triples=triples,
            text=request.text,
            entities_count=entities_count,
            relations_count=relations_count,
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"三元組提取失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/triples/batch")
async def extract_triples_batch(request: TripleBatchRequest) -> JSONResponse:
    """批量三元組提取"""
    service = get_service()

    try:
        results = await service.extract_triples_batch(request.texts)

        response_list = []
        total_triples = 0
        for text, triples in zip(request.texts, results):
            entities_count = len(
                set(
                    [t.subject.text for t in triples] + [t.object.text for t in triples]
                )
            )
            relations_count = len(set(t.relation.type for t in triples))
            total_triples += len(triples)

            response_list.append(
                TripleExtractionResponse(
                    triples=triples,
                    text=text,
                    entities_count=entities_count,
                    relations_count=relations_count,
                )
            )

        response = TripleBatchResponse(
            results=response_list,
            total=len(request.texts),
            processed=len([r for r in results if r]),
            total_triples=total_triples,
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"批量三元組提取失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
