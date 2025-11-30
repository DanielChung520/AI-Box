# 代碼功能說明: MCP 工具測試
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP 工具測試模組"""

import pytest
import tempfile
from mcp.server.tools.task_analyzer import TaskAnalyzerTool
from mcp.server.tools.file_tool import FileTool


@pytest.mark.asyncio
async def test_task_analyzer_tool():
    """測試 Task Analyzer 工具"""
    tool = TaskAnalyzerTool()

    # 測試執行
    result = await tool.execute(
        {"task": "Create a plan for the project", "context": {}}
    )

    assert "task_id" in result
    assert "task_type" in result
    assert "workflow" in result
    assert result["task_type"] in ["planning", "execution", "review", "general"]


@pytest.mark.asyncio
async def test_file_tool_read_write():
    """測試 File Tool 讀寫操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(base_path=tmpdir)

        # 寫入文件
        write_result = await tool.execute(
            {"operation": "write", "path": "test.txt", "content": "Hello, World!"}
        )

        assert write_result["success"] is True

        # 讀取文件
        read_result = await tool.execute({"operation": "read", "path": "test.txt"})

        assert read_result["success"] is True
        assert read_result["content"] == "Hello, World!"


@pytest.mark.asyncio
async def test_file_tool_list():
    """測試 File Tool 列表操作"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = FileTool(base_path=tmpdir)

        # 創建一些文件
        await tool.execute(
            {"operation": "write", "path": "file1.txt", "content": "Content 1"}
        )
        await tool.execute(
            {"operation": "write", "path": "file2.txt", "content": "Content 2"}
        )

        # 列出文件
        list_result = await tool.execute({"operation": "list", "path": "."})

        assert list_result["success"] is True
        assert list_result["type"] == "directory"
        assert len(list_result["items"]) >= 2


@pytest.mark.asyncio
async def test_file_tool_path_validation():
    """測試 File Tool 路徑驗證"""
    tool = FileTool(base_path="/tmp")

    # 嘗試訪問基礎路徑外的文件（應該失敗）
    with pytest.raises(ValueError):
        await tool.execute({"operation": "read", "path": "../../etc/passwd"})
