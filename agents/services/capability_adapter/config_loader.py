# 代碼功能說明: Capability Adapter 配置加載器
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""Capability Adapter 配置加載器

從配置文件加載白名單配置。
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


class CapabilityAdapterConfigLoader:
    """Capability Adapter 配置加載器"""

    def __init__(self, config_path: Optional[str | Path] = None):
        """
        初始化配置加載器

        Args:
            config_path: 配置文件路徑（可選）
        """
        if config_path is None:
            config_path = (
                Path(__file__).resolve().parent.parent.parent.parent
                / "config"
                / "capability_adapter_config.yaml"
            )

        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None

    def load_config(self) -> Dict[str, Any]:
        """
        加載配置文件

        Returns:
            配置字典
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return self._get_default_config()

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f)
            logger.info(f"Loaded capability adapter config from: {self.config_path}")
            return self._config or {}
        except Exception as e:
            logger.error(f"Failed to load config: {e}", exc_info=True)
            return self._get_default_config()

    def get_file_adapter_paths(self) -> List[str]:
        """
        獲取文件適配器允許的路徑列表

        Returns:
            路徑列表
        """
        config = self.load_config()
        return config.get("file_adapter", {}).get("allowed_paths", [])

    def get_database_adapter_tables(self) -> List[str]:
        """
        獲取數據庫適配器允許的表列表

        Returns:
            表名列表
        """
        config = self.load_config()
        return config.get("database_adapter", {}).get("allowed_tables", [])

    def get_api_adapter_endpoints(self) -> List[str]:
        """
        獲取 API 適配器允許的端點列表

        Returns:
            端點列表
        """
        config = self.load_config()
        return config.get("api_adapter", {}).get("allowed_endpoints", [])

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            "file_adapter": {"allowed_paths": []},
            "database_adapter": {"allowed_tables": []},
            "api_adapter": {"allowed_endpoints": []},
        }
