# 代碼功能說明: Excel 編輯器 Agent 單元測試
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""Excel 編輯器 Agent 單元測試

測試 Excel 編輯器 Agent 的基本功能。
"""

import pytest

from agents.builtin.xls_editor.agent import XlsEditingAgent


@pytest.mark.asyncio
async def test_xls_editor_health_check():
    """測試健康檢查"""
    agent = XlsEditingAgent()
    status = await agent.health_check()
    assert status is not None


@pytest.mark.asyncio
async def test_xls_editor_get_capabilities():
    """測試獲取能力"""
    agent = XlsEditingAgent()
    capabilities = await agent.get_capabilities()
    assert capabilities is not None
    assert "agent_id" in capabilities
    assert capabilities["agent_id"] == "xls-editor"
