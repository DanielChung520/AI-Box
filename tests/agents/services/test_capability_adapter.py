# 代碼功能說明: Capability Adapter 單元測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 單元測試

測試 Capability Adapter 的核心功能：參數驗證、作用域限制和結果正規化。
"""

import tempfile
from pathlib import Path

import pytest

from agents.services.capability_adapter import FileAdapter


class TestFileAdapter:
    """File Adapter 測試類"""

    def test_file_adapter_init(self):
        """測試 File Adapter 初始化"""
        adapter = FileAdapter(allowed_paths=["/tmp"])
        assert adapter is not None
        assert len(adapter.allowed_paths) == 1

    def test_validate_allowed_path(self):
        """測試驗證允許的路徑"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FileAdapter(allowed_paths=[tmpdir])
            test_file = Path(tmpdir) / "test.txt"

            validation = adapter.validate({"file_path": str(test_file)})
            assert validation.valid is True

    def test_validate_disallowed_path(self):
        """測試驗證不允許的路徑"""
        adapter = FileAdapter(allowed_paths=["/tmp"])

        validation = adapter.validate({"file_path": "/etc/passwd"})
        assert validation.valid is False
        assert "not in allowed" in validation.reason.lower()

    @pytest.mark.asyncio
    async def test_read_file(self):
        """測試讀取文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FileAdapter(allowed_paths=[tmpdir])
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Hello, World!")

            result = await adapter.execute("read_file", {"file_path": str(test_file)})
            assert result.success is True
            assert result.result is not None
            assert result.result["content"] == "Hello, World!"

    @pytest.mark.asyncio
    async def test_write_file(self):
        """測試寫入文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FileAdapter(allowed_paths=[tmpdir])
            test_file = Path(tmpdir) / "test.txt"

            result = await adapter.execute(
                "write_file", {"file_path": str(test_file), "content": "Test content"}
            )
            assert result.success is True
            assert test_file.exists()
            assert test_file.read_text() == "Test content"

    @pytest.mark.asyncio
    async def test_delete_file(self):
        """測試刪除文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            adapter = FileAdapter(allowed_paths=[tmpdir])
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("Test")

            result = await adapter.execute("delete_file", {"file_path": str(test_file)})
            assert result.success is True
            assert not test_file.exists()
