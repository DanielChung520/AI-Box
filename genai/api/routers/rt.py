# 代碼功能說明: RT 關係類型分類路由
# 創建日期: 2025-01-27 23:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27 23:30 (UTC+8)

"""RT 關係類型分類路由 - 提供關係類型分類 API 端點"""

from typing import Optional

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from genai.api.models.rt_models import RTBatchRequest, RTBatchResponse, RTRequest, RTResponse
from genai.api.services.rt_service import RTService

router = APIRouter(prefix="/text-analysis", tags=["RT"])

# 全局服務實例（懶加載）
_service: Optional[RTService] = None


def get_service() -> RTService:
    """獲取 RT 服務實例（單例模式）"""
    global _service
    if _service is None:
        _service = RTService()
    return _service


@router.post("/rt")
async def classify_relation_type(request: RTRequest) -> JSONResponse:
    """關係類型分類"""
    service = get_service()

    try:
        relation_types = await service.classify_relation_type(
            request.relation_text,
            request.subject_text,
            request.object_text,
            request.model_type,
        )
        model_used = request.model_type or service.model_type

        # 獲取主要類型（置信度最高的）
        primary_type = relation_types[0].type if relation_types else None

        response = RTResponse(
            relation_text=request.relation_text,
            relation_types=relation_types,
            primary_type=primary_type,
            model_used=model_used,
        )

        return APIResponse.success(data=response.model_dump())
    except RuntimeError as e:
        return APIResponse.error(
            message=f"關係類型分類失敗: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except Exception as e:
        return APIResponse.error(
            message=f"關係類型分類失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/rt/batch")
async def classify_relation_types_batch(request: RTBatchRequest) -> JSONResponse:
    """批量關係類型分類"""
    service = get_service()

    try:
        requests_data = [
            {
                "relation_text": r.relation_text,
                "subject_text": r.subject_text,
                "object_text": r.object_text,
            }
            for r in request.relations
        ]
        results = await service.classify_relation_types_batch(requests_data, request.model_type)
        model_used = request.model_type or service.model_type

        response_list = []
        for req, relation_types in zip(request.relations, results):
            primary_type = relation_types[0].type if relation_types else None
            response_list.append(
                RTResponse(
                    relation_text=req.relation_text,
                    relation_types=relation_types,
                    primary_type=primary_type,
                    model_used=model_used,
                )
            )

        response = RTBatchResponse(
            results=response_list,
            total=len(request.relations),
            processed=len([r for r in results if r]),
        )

        return APIResponse.success(data=response.model_dump())
    except Exception as e:
        return APIResponse.error(
            message=f"批量關係類型分類失敗: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
