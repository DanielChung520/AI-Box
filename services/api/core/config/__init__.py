# 代碼功能說明: 配置定義模組導出
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-20

"""配置定義模組

提供配置元數據機制的核心功能：
- DefinitionLoader: 從 JSON 文件加載配置定義到內存緩存
- get_definition_loader: 獲取 DefinitionLoader 單例
- initialize_config_system: 初始化配置系統（API 啟動時調用）
"""

import logging
from typing import Optional

from .definition_loader import DefinitionLoader, get_definition_loader

logger = logging.getLogger(__name__)

__all__ = ["DefinitionLoader", "get_definition_loader", "initialize_config_system"]

_definition_loader: Optional[DefinitionLoader] = None


def initialize_config_system() -> DefinitionLoader:
    """
    初始化配置系統

    在 API 啟動時調用，將所有配置定義 JSON 文件加載到內存緩存。

    Returns:
        DefinitionLoader: 配置定義加載器實例

    Example:
        ```python
        # 在 api/main.py 的 startup event 中調用
        from services.api.core.config import initialize_config_system

        @app.on_event("startup")
        async def startup_event():
            initialize_config_system()
        ```
    """
    global _definition_loader
    if _definition_loader is None:
        _definition_loader = DefinitionLoader()
        definitions = _definition_loader.load_all()
        logger.info(
            f"Config metadata system initialized: {len(definitions)} definitions loaded",
            extra={"count": len(definitions), "scopes": list(definitions.keys())},
        )
    else:
        logger.info("Config metadata system already initialized, skipping")
    return _definition_loader
