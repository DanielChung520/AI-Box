# 代碼功能說明: 配置管理模組初始化文件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""系統配置管理模組 - 提供統一的配置讀取功能"""

from .config import load_project_config, get_config_section

__all__ = ["load_project_config", "get_config_section"]
