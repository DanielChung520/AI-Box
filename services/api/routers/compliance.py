# 代碼功能說明: 合規檢查 API 路由（WBS-4.3: 合規檢查框架）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""合規檢查 API 路由

提供合規檢查和報告生成功能。
"""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.api.services.compliance_service import (
    ComplianceReport,
    ComplianceStandard,
    get_compliance_service,
)
from system.security.dependencies import get_current_user
from system.security.models import User

router = APIRouter(prefix="/compliance", tags=["Compliance"])


class ComplianceCheckRequest(BaseModel):
    """合規檢查請求"""

    standards: Optional[List[ComplianceStandard]] = None


@router.get("/check")
async def check_compliance(
    standards: Optional[str] = None,
    current_user: User = Depends(get_current_user),
) -> ComplianceReport:
    """
    執行合規檢查

    Args:
        standards: 要檢查的標準（逗號分隔，如 "iso_42001,aigp"）
        current_user: 當前用戶

    Returns:
        合規報告
    """
    try:
        service = get_compliance_service()

        # 解析標準列表
        standards_list: Optional[List[ComplianceStandard]] = None
        if standards:
            standards_list = [ComplianceStandard(s.strip()) for s in standards.split(",")]

        report = service.generate_compliance_report(standards=standards_list)
        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合規檢查失敗: {str(e)}")


@router.get("/check/{standard}")
async def check_single_standard(
    standard: ComplianceStandard,
    current_user: User = Depends(get_current_user),
) -> ComplianceReport:
    """
    檢查單一標準的合規性

    Args:
        standard: 合規標準
        current_user: 當前用戶

    Returns:
        合規報告
    """
    try:
        service = get_compliance_service()
        report = service.generate_compliance_report(standards=[standard])
        return report

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"合規檢查失敗: {str(e)}")
