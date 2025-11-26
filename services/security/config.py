# 代碼功能說明: 安全模組配置管理
# 創建日期: 2025-11-26 01:30 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:30 (UTC+8)

"""安全模組配置管理 - 讀取 config.json 和環境變數。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from core.config import get_config_section


@dataclass(frozen=True)
class JWTConfig:
    """JWT 配置"""

    enabled: bool
    secret_key: str
    algorithm: str
    expiration_hours: int

    @classmethod
    def from_dict(cls, data: dict, env_prefix: str = "SECURITY_JWT") -> "JWTConfig":
        """從字典和環境變數創建 JWT 配置"""
        return cls(
            enabled=os.getenv(
                f"{env_prefix}_ENABLED", str(data.get("enabled", False))
            ).lower()
            == "true",
            secret_key=os.getenv(
                f"{env_prefix}_SECRET_KEY",
                data.get("secret_key", "SECURITY_JWT_SECRET_KEY"),
            ),
            algorithm=os.getenv(
                f"{env_prefix}_ALGORITHM", data.get("algorithm", "HS256")
            ),
            expiration_hours=int(
                os.getenv(
                    f"{env_prefix}_EXPIRATION_HOURS", data.get("expiration_hours", 24)
                )
            ),
        )


@dataclass(frozen=True)
class APIKeyConfig:
    """API Key 配置"""

    enabled: bool

    @classmethod
    def from_dict(
        cls, data: dict, env_prefix: str = "SECURITY_API_KEY"
    ) -> "APIKeyConfig":
        """從字典和環境變數創建 API Key 配置"""
        return cls(
            enabled=os.getenv(
                f"{env_prefix}_ENABLED", str(data.get("enabled", False))
            ).lower()
            == "true",
        )


@dataclass(frozen=True)
class RBACConfig:
    """RBAC 配置"""

    enabled: bool

    @classmethod
    def from_dict(cls, data: dict, env_prefix: str = "SECURITY_RBAC") -> "RBACConfig":
        """從字典和環境變數創建 RBAC 配置"""
        return cls(
            enabled=os.getenv(
                f"{env_prefix}_ENABLED", str(data.get("enabled", False))
            ).lower()
            == "true",
        )


@dataclass(frozen=True)
class SecuritySettings:
    """安全模組設定"""

    enabled: bool
    mode: str  # development, production
    jwt: JWTConfig
    api_key: APIKeyConfig
    rbac: RBACConfig

    @property
    def is_development_mode(self) -> bool:
        """是否為開發模式"""
        return self.mode.lower() == "development"

    @property
    def should_bypass_auth(self) -> bool:
        """是否應該繞過認證檢查"""
        return not self.enabled or self.is_development_mode


@lru_cache
def get_security_settings() -> SecuritySettings:
    """載入安全設定並允許環境變數覆寫。

    配置來源優先級：
    1. 環境變數（SECURITY_ENABLED, SECURITY_MODE 等）
    2. config.json 中的 services.security 區塊
    3. 預設值

    Returns:
        SecuritySettings: 安全設定物件
    """
    section = get_config_section("services", "security", default={}) or {}

    # 讀取 enabled 和 mode（環境變數優先）
    enabled_env = os.getenv("SECURITY_ENABLED", "").lower()
    enabled = enabled_env == "true" if enabled_env else section.get("enabled", False)

    mode_env = os.getenv("SECURITY_MODE", "").lower()
    mode = (
        mode_env
        if mode_env in ("development", "production")
        else section.get("mode", "development")
    )

    # 讀取子配置
    jwt_data = section.get("jwt", {})
    jwt_config = JWTConfig.from_dict(jwt_data)

    api_key_data = section.get("api_key", {})
    api_key_config = APIKeyConfig.from_dict(api_key_data)

    rbac_data = section.get("rbac", {})
    rbac_config = RBACConfig.from_dict(rbac_data)

    return SecuritySettings(
        enabled=enabled,
        mode=mode,
        jwt=jwt_config,
        api_key=api_key_config,
        rbac=rbac_config,
    )
