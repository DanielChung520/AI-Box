# 代碼功能說明: 文件存儲適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""文件存儲適配器 - 重新導出 storage 模組的內容"""

from storage.file_storage import (
    FileStorage,
    LocalFileStorage,
    create_storage_from_config,
)

__all__ = [
    "FileStorage",
    "LocalFileStorage",
    "create_storage_from_config",
]
