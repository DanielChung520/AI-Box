# 代碼功能說明: ArangoDB 設定載入模組
# 創建日期: 2025-11-25 22:58 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25 22:58 (UTC+8)

"""提供 ArangoDB 設定結構與配置載入輔助函式。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, Field

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.json"
_CONFIG_TEMPLATE_PATH = _PROJECT_ROOT / "config" / "config.example.json"
_SETTINGS_CACHE: Dict[str, "ArangoDBSettings"] = {}


class CredentialEnv(BaseModel):
    """儲存用於讀取憑證的環境變數名稱。"""

    username: str = Field(default="ARANGODB_USERNAME", description="使用者名稱環境變數")
    password: str = Field(default="ARANGODB_PASSWORD", description="密碼環境變數")


class RetrySettings(BaseModel):
    """連線重試設定。"""

    enabled: bool = Field(default=True, description="是否啟用重試")
    max_attempts: int = Field(default=3, ge=1, description="最大重試次數")
    backoff_factor: float = Field(default=1.5, gt=0, description="退避係數")
    max_backoff_seconds: float = Field(default=10.0, gt=0, description="最大退避秒數")


class PoolSettings(BaseModel):
    """連線池設定。"""

    connections: int = Field(default=10, ge=1, description="初始連線數")
    max_size: int = Field(default=10, ge=1, description="最大連線數")
    timeout: Optional[float] = Field(default=None, ge=0, description="等待可用連線的逾時秒數")


class TLSSettings(BaseModel):
    """TLS/SSL 設定。"""

    enabled: bool = Field(default=False, description="是否啟用 TLS")
    verify: bool = Field(default=True, description="是否驗證憑證")
    ca_file: Optional[str] = Field(default=None, description="自訂 CA 憑證路徑（可為 None）")


class ArangoDBSettings(BaseModel):
    """ArangoDB 連線設定。"""

    host: str = Field(default_factory=lambda: os.getenv("ARANGODB_HOST", "localhost"))
    port: int = Field(default_factory=lambda: int(os.getenv("ARANGODB_PORT", "8529")))
    protocol: str = Field(
        default_factory=lambda: os.getenv("ARANGODB_PROTOCOL", "http"),
        pattern="^(http|https)$",
    )
    database: str = Field(
        default_factory=lambda: os.getenv("ARANGODB_DATABASE", "ai_box_kg")
    )
    request_timeout: float = Field(default=30.0, gt=0)
    credentials: CredentialEnv = Field(default_factory=CredentialEnv)
    retry: RetrySettings = Field(default_factory=RetrySettings)
    pool: PoolSettings = Field(default_factory=PoolSettings)
    tls: TLSSettings = Field(default_factory=TLSSettings)

    def with_overrides(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        protocol: Optional[str] = None,
        request_timeout: Optional[float] = None,
    ) -> "ArangoDBSettings":
        """建立覆寫部分欄位的新設定。"""
        update_payload: Dict[str, Any] = {}
        if host is not None:
            update_payload["host"] = host
        if port is not None:
            update_payload["port"] = port
        if database is not None:
            update_payload["database"] = database
        if protocol is not None:
            update_payload["protocol"] = protocol
        if request_timeout is not None:
            update_payload["request_timeout"] = request_timeout
        if not update_payload:
            return self
        return self.model_copy(update=update_payload)

    @property
    def base_url(self) -> str:
        """回傳連線主機 URL。"""
        return f"{self.protocol}://{self.host}:{self.port}"


def _read_json(path: Path) -> Dict[str, Any]:
    """讀取 JSON 配置檔案。"""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fp:
            return json.load(fp)
    except json.JSONDecodeError as exc:
        raise ValueError(f"無法解析配置檔案 {path}: {exc}") from exc


def _load_datastore_section(config: Dict[str, Any]) -> Dict[str, Any]:
    """從整體配置擷取 ArangoDB 區段。"""
    return (config.get("datastores") or {}).get("arangodb") or {}


def _build_settings_from_sources(
    config_path: Optional[Union[str, Path]]
) -> ArangoDBSettings:
    """依序讀取 config.json 與樣板建立設定。"""
    data: Dict[str, Any] = {}
    candidate_paths = []
    if config_path:
        candidate_paths.append(Path(config_path))
    candidate_paths.extend([_DEFAULT_CONFIG_PATH, _CONFIG_TEMPLATE_PATH])

    for path in candidate_paths:
        if path and path.exists():
            data = _load_datastore_section(_read_json(path))
            if data:
                break

    return ArangoDBSettings(**data)


def load_arangodb_settings(
    config_path: Optional[Union[str, Path]] = None,
    *,
    force_reload: bool = False,
) -> ArangoDBSettings:
    """
    載入 ArangoDB 設定。

    Args:
        config_path: 自訂配置檔案路徑
        force_reload: 是否強制重新讀取
    """
    cache_key = str(Path(config_path).resolve()) if config_path else "__default__"
    if not force_reload and cache_key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[cache_key]

    settings = _build_settings_from_sources(config_path)
    _SETTINGS_CACHE[cache_key] = settings
    return settings


def clear_arangodb_settings_cache() -> None:
    """清除設定快取（供測試或重新載入使用）。"""
    _SETTINGS_CACHE.clear()
