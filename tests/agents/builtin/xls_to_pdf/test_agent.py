# 代碼功能說明: Excel 轉 PDF Agent 單元測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel 轉 PDF Agent 單元測試

測試 Excel 轉 PDF Agent 的基本功能。
"""

import pytest

from agents.builtin.xls_to_pdf.agent import XlsToPdfAgent


@pytest.mark.asyncio
async def test_xls_to_pdf_health_check():
    """測試健康檢查"""
    agent = XlsToPdfAgent()
    status = await agent.health_check()
    assert status is not None


@pytest.mark.asyncio
async def test_xls_to_pdf_get_capabilities():
    """測試獲取能力"""
    agent = XlsToPdfAgent()
    capabilities = await agent.get_capabilities()
    assert capabilities is not None
    assert "agent_id" in capabilities
    assert capabilities["agent_id"] == "xls-to-pdf"
