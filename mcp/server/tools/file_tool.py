# 代碼功能說明: File Tool 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""File Tool 實現模組"""

import logging
from typing import Dict, Any
from pathlib import Path
from mcp.server.tools.base import BaseTool

logger = logging.getLogger(__name__)


class FileTool(BaseTool):
    """文件操作工具"""

    def __init__(self, base_path: str = "/tmp"):
        """
        初始化 File Tool

        Args:
            base_path: 基礎路徑（用於安全限制）
        """
        self.base_path = Path(base_path).resolve()
        super().__init__(
            name="file_tool",
            description="文件讀寫操作工具",
            input_schema={
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["read", "write", "list", "delete"],
                        "description": "操作類型",
                    },
                    "path": {
                        "type": "string",
                        "description": "文件路徑（相對於 base_path）",
                    },
                    "content": {
                        "type": "string",
                        "description": "文件內容（僅用於 write 操作）",
                    },
                },
                "required": ["operation", "path"],
            },
        )

    def _validate_path(self, path: str) -> Path:
        """
        驗證並規範化路徑

        Args:
            path: 文件路徑

        Returns:
            Path: 規範化後的路徑

        Raises:
            ValueError: 如果路徑不安全
        """
        # 解析路徑
        full_path = (self.base_path / path).resolve()

        # 檢查是否在基礎路徑內
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(f"Path '{path}' is outside allowed base path")

        return full_path

    async def execute(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行文件操作

        Args:
            arguments: 工具參數

        Returns:
            Dict[str, Any]: 操作結果
        """
        operation = arguments.get("operation")
        path = arguments.get("path")
        content = arguments.get("content", "")

        if not operation or not path:
            raise ValueError("operation and path are required")

        try:
            file_path = self._validate_path(path)

            if operation == "read":
                if not file_path.exists():
                    return {"success": False, "error": f"File not found: {path}"}
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                return {
                    "success": True,
                    "path": str(file_path),
                    "content": file_content,
                    "size": len(file_content),
                }

            elif operation == "write":
                # 確保目錄存在
                file_path.parent.mkdir(parents=True, exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
                return {
                    "success": True,
                    "path": str(file_path),
                    "message": "File written successfully",
                    "size": len(content),
                }

            elif operation == "list":
                if not file_path.exists():
                    return {"success": False, "error": f"Path not found: {path}"}
                if file_path.is_file():
                    return {
                        "success": True,
                        "path": str(file_path),
                        "type": "file",
                        "size": file_path.stat().st_size,
                    }
                else:
                    items = []
                    for item in file_path.iterdir():
                        items.append(
                            {
                                "name": item.name,
                                "type": "directory" if item.is_dir() else "file",
                                "size": item.stat().st_size if item.is_file() else 0,
                            }
                        )
                    return {
                        "success": True,
                        "path": str(file_path),
                        "type": "directory",
                        "items": items,
                    }

            elif operation == "delete":
                if not file_path.exists():
                    return {"success": False, "error": f"Path not found: {path}"}
                if file_path.is_file():
                    file_path.unlink()
                else:
                    import shutil

                    shutil.rmtree(file_path)
                return {
                    "success": True,
                    "path": str(file_path),
                    "message": "Deleted successfully",
                }

            else:
                return {"success": False, "error": f"Unknown operation: {operation}"}

        except Exception as e:
            logger.error(f"File operation error: {e}")
            return {"success": False, "error": str(e)}
