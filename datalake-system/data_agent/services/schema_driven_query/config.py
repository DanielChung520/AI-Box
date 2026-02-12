# 代碼功能說明: Data-Agent-JP 配置模組
# 創建日期: 2026-02-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-10

"""Data-Agent-JP 配置管理

支援：
- Pydantic Settings
- 環境變數覆寫
- 多來源配置
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class OracleConfig(BaseSettings):
    """Oracle 資料庫配置"""

    host: str = "192.168.5.16"
    port: int = 1521
    service_name: str = "ORCL"
    user: str = "appuser"
    password: str = "app123"
    lib_path: str = "/home/daniel/instantclient_23_26"
    libaio_path: str = "/home/daniel/oracle_libs"

    @property
    def dsn(self) -> str:
        """返回 Oracle DSN"""
        return f"{self.host}:{self.port}/{self.service_name}"

    class Config:
        env_prefix = "DATA_AGENT_JP_ORACLE_"


class QdrantConfig(BaseSettings):
    """Qdrant 配置"""

    host: str = "localhost"
    port: int = 6333
    collection_prefix: str = "jp_"
    use_qdrant: bool = True

    class Config:
        env_prefix = "DATA_AGENT_JP_QDRANT_"


class ArangoDBConfig(BaseSettings):
    """ArangoDB 配置"""

    host: str = "localhost"
    port: int = 8529
    database: str = "schema_registry_db"
    collection_prefix: str = "jp_"
    username: str = "root"
    password: str = ""
    use_arangodb: bool = True

    @property
    def url(self) -> str:
        """返回 ArangoDB URL"""
        return f"http://{self.host}:{self.port}"

    class Config:
        env_prefix = "DATA_AGENT_JP_ARANGODB_"


class S3Config(BaseSettings):
    """S3 配置

    從環境變數載入（參照 datalake-system/.env）：
    - DATALAKE_SEAWEEDFS_S3_ENDPOINT: http://localhost:8334
    - DATALAKE_SEAWEEDFS_S3_ACCESS_KEY: admin
    - DATALAKE_SEAWEEDFS_S3_SECRET_KEY: admin123
    - DATALAKE_SEAWEEDFS_USE_SSL: false
    - DATALAKE_SEAWEEDFS_S3_BUCKET: tiptop-raw
    """

    endpoint: str = "localhost:8334"
    access_key: str = "admin"
    secret_key: str = "admin123"
    bucket: str = "tiptop-raw"
    path_prefix: str = "raw/v1/tiptop_jp"
    region: str = "us-east-1"
    use_ssl: bool = False
    url_style: str = "path"

    class Config:
        env_prefix = "DATALAKE_SEAWEEDFS_S3_"

    @property
    def endpoint_host(self) -> str:
        """返回 endpoint（不含 http://，供 DuckDB 使用）"""
        ep = self.endpoint
        if ep.startswith("http://"):
            return ep[7:]
        elif ep.startswith("https://"):
            return ep[8:]
        return ep


class DuckDBConfig(BaseSettings):
    """DuckDB 配置"""

    s3: S3Config = Field(default_factory=S3Config)
    memory_limit: str = "8GB"
    threads: int = 4
    temp_directory: str = "/tmp/duckdb"
    enable_external_access: bool = True

    class Config:
        env_prefix = "DATA_AGENT_JP_DUCKDB_"


class LLMConfig(BaseSettings):
    """LLM 配置"""

    endpoint: str = "http://localhost:11434"
    model: str = "qwen3-coder:30b"
    fallback_model: str = "gpt-oss:120b"
    temperature: float = 0.3
    timeout: int = 30

    class Config:
        env_prefix = "DATA_AGENT_JP_LLM_"


class SchemaDrivenQueryConfig(BaseSettings):
    """Data-Agent-JP 主配置"""

    # Metadata 路徑
    metadata_path: str = "/home/daniel/ai-box/datalake-system/metadata"

    # 子系統 ID
    system_id: str = "tiptop_jp"

    # 資料來源選擇
    datasource: str = "DUCKDB"
    enable_oracle_fallback: bool = False

    # 子配置
    oracle: OracleConfig = Field(default_factory=OracleConfig)
    duckdb: DuckDBConfig = Field(default_factory=DuckDBConfig)
    qdrant: QdrantConfig = Field(default_factory=QdrantConfig)
    arangodb: ArangoDBConfig = Field(default_factory=ArangoDBConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    # 查詢配置
    default_timeout: int = 30
    max_results: int = 1000

    # 載入策略
    load_from_db_first: bool = True
    fallback_to_file: bool = True

    # 日誌等級
    log_level: str = "INFO"

    class Config:
        env_prefix = "DATA_AGENT_JP_"

    @property
    def concepts_path(self) -> Path:
        """Concepts JSON 路徑"""
        return Path(self.metadata_path) / "systems" / self.system_id / "concepts.json"

    @property
    def intents_path(self) -> Path:
        """Intents JSON 路徑"""
        return Path(self.metadata_path) / "systems" / self.system_id / "intents.json"

    @property
    def bindings_path(self) -> Path:
        """Bindings JSON 路徑"""
        return Path(self.metadata_path) / "systems" / self.system_id / "bindings.json"

    @property
    def schema_path(self) -> Path:
        """Schema YAML 路徑"""
        return Path(self.metadata_path) / "systems" / self.system_id / f"{self.system_id}.yml"


def get_config() -> SchemaDrivenQueryConfig:
    """獲取配置實例"""
    return SchemaDrivenQueryConfig()
