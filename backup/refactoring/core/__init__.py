# 代碼功能說明: Core 配置適配器（向後兼容）
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Core 配置適配器 - 重新導出 system.infra.config 的模組"""

from system.infra.config.config import load_project_config, get_config_section

__all__ = ["load_project_config", "get_config_section"]
