# 代碼功能說明: MCP Server 配置管理
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Server 配置管理模組"""

from typing import Optional

try:
    from pydantic import ConfigDict, Field
    from pydantic_settings import BaseSettings  # type: ignore[attr-defined]
except ImportError:
    # 兼容 pydantic v1
    from pydantic import BaseSettings, Field  # type: ignore[no-redef]

    ConfigDict = None  # type: ignore[assignment, misc]


class MCPServerConfig(BaseSettings):
    """MCP Server 配置類"""

    # 服務器基本配置
    server_name: str = Field(default="ai-box-mcp-server", description="服務器名稱")
    server_version: str = Field(default="1.0.0", description="服務器版本")
    protocol_version: str = Field(default="2024-11-05", description="協議版本")

    # 網絡配置
    host: str = Field(default="0.0.0.0", description="服務器主機地址")  # nosec B104
    port: int = Field(default=8002, description="服務器端口")

    # 日誌配置
    log_level: str = Field(default="INFO", description="日誌級別")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="日誌格式",
    )

    # 監控配置
    enable_monitoring: bool = Field(default=True, description="是否啟用監控")
    metrics_endpoint: str = Field(default="/metrics", description="指標端點")

    # 工具配置
    tools_config_path: Optional[str] = Field(default=None, description="工具配置文件路徑")

    # 優雅關閉配置
    shutdown_timeout: int = Field(default=30, description="關閉超時時間（秒）")

    if ConfigDict is not None:
        model_config = ConfigDict(  # type: ignore[assignment]  # ConfigDict 兼容 SettingsConfigDict
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="ignore",  # 忽略未定義的環境變數，避免 Pydantic 驗證錯誤
        )
    else:
        # Pydantic v1 兼容
        class Config:  # type: ignore[no-redef]
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "ignore"  # 忽略未定義的環境變數


def get_config() -> MCPServerConfig:
    """
    獲取 MCP Server 配置

    Returns:
        MCPServerConfig: 配置實例
    """
    return MCPServerConfig()
