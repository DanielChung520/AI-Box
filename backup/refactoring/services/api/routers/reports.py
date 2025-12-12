# 代碼功能說明: Reports API 路由
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Reports API 路由 - 提供報告生成接口"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi import status as http_status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from services.api.core.response import APIResponse
from agents.services.processing.aggregator import ResultAggregator
from agents.services.processing.report_generator import ReportGenerator
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter()


class GenerateReportRequest(BaseModel):
    """生成報告請求模型"""

    task_results: List[Dict[str, Any]] = Field(..., description="Agent 執行結果列表")
    task_id: Optional[str] = Field(None, description="任務 ID")
    report_title: Optional[str] = Field(None, description="報告標題")
    include_output_files: bool = Field(
        default=True, description="是否包含產出物文件鏈接"
    )


@router.post("/reports/generate", status_code=http_status.HTTP_200_OK)
async def generate_report(
    request: GenerateReportRequest,
    user: Optional[User] = Depends(get_current_user),
) -> JSONResponse:
    """
    生成最終報告

    Args:
        request: 生成報告請求
        user: 當前認證用戶（可選）

    Returns:
        報告數據（包含 HTML 內容）
    """
    try:
        # 聚合結果
        aggregator = ResultAggregator()
        aggregated = aggregator.aggregate_results(
            task_results=request.task_results, task_id=request.task_id
        )

        # 生成報告
        generator = ReportGenerator()
        report_data = await generator.generate_report(
            aggregated_results=aggregated,
            report_title=request.report_title,
            include_output_files=request.include_output_files,
        )

        return APIResponse.success(
            data=report_data,
            message="Report generated successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate report: {str(e)}",
        )
