# 代碼功能說明: Markdown 轉 PDF Agent 單元測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Markdown 轉 PDF Agent 單元測試

測試 Markdown 轉 PDF Agent 的基本功能。
"""

import pytest

from agents.builtin.md_to_pdf.agent import MdToPdfAgent


@pytest.mark.asyncio
async def test_md_to_pdf_health_check():
    """測試健康檢查"""
    agent = MdToPdfAgent()
    status = await agent.health_check()
    assert status is not None


@pytest.mark.asyncio
async def test_md_to_pdf_get_capabilities():
    """測試獲取能力"""
    agent = MdToPdfAgent()
    capabilities = await agent.get_capabilities()
    assert capabilities is not None
    assert "agent_id" in capabilities
    assert capabilities["agent_id"] == "md-to-pdf"
