# 代碼功能說明: Data Agent 配置管理器
# 創建日期: 2026-01-30
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-30

"""Data Agent 配置管理器"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class DataAgentConfig:
    """Data Agent 配置管理器"""

    def __init__(self, config_path: Optional[str] = None, env_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路徑（可選）
            env_path: 環境變數文件路徑（可選）
        """
        # 優先加載環境變數
        if env_path is None:
            # 默認使用 data_agent/.env
            current_dir = Path(__file__).resolve().parent
            env_path = str(current_dir / ".env")

        # 加載 .env 文件
        if os.path.exists(env_path):
            load_dotenv(dotenv_path=env_path)
            logger.info(f"已加載環境變數配置: {env_path}")
        else:
            logger.warning(f"環境變數配置文件不存在: {env_path}")

        # 設置配置文件路徑
        self._config_path = config_path or self._get_default_config_path()
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _get_default_config_path(self) -> str:
        """獲取默認配置文件路徑"""
        current_dir = Path(__file__).resolve().parent
        return str(current_dir / "DataAgentConfig.json")

    def _load_config(self) -> None:
        """加載配置文件"""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            logger.info(f"配置文件加載成功: {self._config_path}")
        except FileNotFoundError:
            logger.warning(f"配置文件不存在，使用默認配置: {self._config_path}")
            self._config = self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"配置文件 JSON 格式錯誤: {e}，使用默認配置")
            self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"加載配置文件失敗: {e}，使用默認配置")
            self._config = self._get_default_config()

    def _get_env_value(self, key: str, default: Any = None) -> Any:
        """獲取環境變數值（優先於 JSON 配置）"""
        value = os.getenv(key)
        if value is not None:
            # 嘗試轉換為適當的類型
            if isinstance(default, bool):
                return value.lower() in ("true", "1", "yes", "on")
            elif isinstance(default, int):
                try:
                    return int(value)
                except ValueError:
                    return default
            elif isinstance(default, float):
                try:
                    return float(value)
                except ValueError:
                    return default
            elif isinstance(default, list):
                return value.split(",") if value else []
            return value
        return default

    def _get_default_config(self) -> Dict[str, Any]:
        """獲取默認配置"""
        return {
            "llm": {
                "model_priority": ["qwen3-coder:480b-cloud", "qwen3-coder:30b", "mistral-nemo:12b"],
                "default_temperature": 0.3,
                "default_max_tokens": 1000,
                "fallback_enabled": True,
            },
            "sql": {
                "timeout_seconds": 30,
                "max_rows": 1000,
                "enable_validation": True,
                "dangerous_keywords": [
                    "DROP",
                    "DELETE",
                    "TRUNCATE",
                    "ALTER",
                    "CREATE",
                    "INSERT",
                    "UPDATE",
                ],
                "require_parameters": True,
            },
            "datalake": {
                "default_bucket": "tiptop-raw",
                "default_query_type": "table",
                "timeout_seconds": 60,
                "max_rows_per_file": 10000,
                "enable_cache": True,
            },
            "query_gateway": {
                "timeout_seconds": 30,
                "enable_injection_protection": True,
                "enable_permission_check": True,
                "enable_sensitive_data_masking": True,
            },
            "validation": {
                "schema_enabled": True,
                "data_validation_enabled": True,
                "confidence_threshold": 0.5,
            },
            "logging": {
                "level": "INFO",
                "enable_conversion_log": True,
                "enable_performance_log": True,
            },
        }

    def get_llm_models(self) -> List[str]:
        """獲取 LLM 模型優先級列表（優先從環境變數讀取）"""
        # 從環境變數讀取
        env_models = self._get_env_value("DATA_AGENT_MODEL_PRIORITY", [])
        if env_models:
            return [m.strip() for m in env_models if m.strip()]

        # 從 JSON 配置讀取
        return self._config.get("llm", {}).get("model_priority", [])

    def get_ollama_url(self) -> str:
        """獲取 Ollama URL（優先從環境變數讀取）"""
        return self._get_env_value("DATA_AGENT_OLLAMA_URL", "http://localhost:11434")

    def get_ollama_api_key(self) -> Optional[str]:
        """獲取 Ollama API Key（優先從環境變數讀取）"""
        return self._get_env_value("DATA_AGENT_OLLAMA_API_KEY", None)

    def get_llm_temperature(self) -> float:
        """獲取 LLM 默認溫度"""
        default = self._config.get("llm", {}).get("default_temperature", 0.3)
        return self._get_env_value("DATA_AGENT_LLM_TEMPERATURE", default)

    def get_llm_max_tokens(self) -> int:
        """獲取 LLM 默認最大 token 數"""
        default = self._config.get("llm", {}).get("default_max_tokens", 1000)
        return self._get_env_value("DATA_AGENT_LLM_MAX_TOKENS", default)

    def is_llm_fallback_enabled(self) -> bool:
        """是否啟用 LLM 回退機制"""
        default = self._config.get("llm", {}).get("fallback_enabled", True)
        return self._get_env_value("DATA_AGENT_LLM_FALLBACK_ENABLED", default)

    def get_sql_timeout(self) -> int:
        """獲取 SQL 查詢超時時間（秒）"""
        default = self._config.get("sql", {}).get("timeout_seconds", 30)
        return self._get_env_value("DATA_AGENT_SQL_TIMEOUT_SECONDS", default)

    def get_sql_max_rows(self) -> int:
        """獲取 SQL 查詢最大行數"""
        default = self._config.get("sql", {}).get("max_rows", 1000)
        return self._get_env_value("DATA_AGENT_SQL_MAX_ROWS", default)

    def is_sql_validation_enabled(self) -> bool:
        """是否啟用 SQL 驗證"""
        default = self._config.get("sql", {}).get("enable_validation", True)
        return self._get_env_value("DATA_AGENT_SQL_VALIDATION_ENABLED", default)

    def get_dangerous_keywords(self) -> List[str]:
        """獲取危險關鍵字列表"""
        return self._config.get("sql", {}).get("dangerous_keywords", [])

    def is_require_parameters(self) -> bool:
        """是否要求參數化查詢"""
        default = self._config.get("sql", {}).get("require_parameters", True)
        return self._get_env_value("DATA_AGENT_SQL_REQUIRE_PARAMETERS", default)

    def get_datalake_bucket(self) -> str:
        """獲取默認 DataLake bucket"""
        default = self._config.get("datalake", {}).get("default_bucket", "tiptop-raw")
        return self._get_env_value("DATA_AGENT_DATALAKE_BUCKET", default)

    def get_datalake_query_type(self) -> str:
        """獲取默認 DataLake 查詢類型"""
        default = self._config.get("datalake", {}).get("default_query_type", "table")
        return self._get_env_value("DATA_AGENT_DATALAKE_QUERY_TYPE", default)

    def get_datalake_timeout(self) -> int:
        """獲取 DataLake 查詢超時時間（秒）"""
        default = self._config.get("datalake", {}).get("timeout_seconds", 60)
        return self._get_env_value("DATA_AGENT_DATALAKE_TIMEOUT_SECONDS", default)

    def get_datalake_max_rows(self) -> int:
        """獲取 DataLake 查詢最大行數"""
        default = self._config.get("datalake", {}).get("max_rows_per_file", 10000)
        return self._get_env_value("DATA_AGENT_DATALAKE_MAX_ROWS", default)

    def is_datalake_cache_enabled(self) -> bool:
        """是否啟用 DataLake 緩存"""
        default = self._config.get("datalake", {}).get("enable_cache", True)
        return self._get_env_value("DATA_AGENT_DATALAKE_CACHE_ENABLED", default)

    def get_query_gateway_timeout(self) -> int:
        """獲取 Query Gateway 超時時間（秒）"""
        default = self._config.get("query_gateway", {}).get("timeout_seconds", 30)
        return self._get_env_value("DATA_AGENT_QUERY_GATEWAY_TIMEOUT_SECONDS", default)

    def is_injection_protection_enabled(self) -> bool:
        """是否啟用 SQL 注入防護"""
        default = self._config.get("query_gateway", {}).get("enable_injection_protection", True)
        return self._get_env_value("DATA_AGENT_QUERY_GATEWAY_INJECTION_PROTECTION", default)

    def is_permission_check_enabled(self) -> bool:
        """是否啟用權限檢查"""
        default = self._config.get("query_gateway", {}).get("enable_permission_check", True)
        return self._get_env_value("DATA_AGENT_QUERY_GATEWAY_PERMISSION_CHECK", default)

    def is_sensitive_data_masking_enabled(self) -> bool:
        """是否啟用敏感數據脫敏"""
        default = self._config.get("query_gateway", {}).get("enable_sensitive_data_masking", True)
        return self._get_env_value("DATA_AGENT_QUERY_GATEWAY_SENSITIVE_DATA_MASKING", default)

    def get_confidence_threshold(self) -> float:
        """獲取置信度閾值"""
        default = self._config.get("validation", {}).get("confidence_threshold", 0.5)
        return self._get_env_value("DATA_AGENT_VALIDATION_CONFIDENCE_THRESHOLD", default)

    def get_logging_level(self) -> str:
        """獲取日誌級別"""
        default = self._config.get("logging", {}).get("level", "INFO")
        return self._get_env_value("DATA_AGENT_LOGGING_LEVEL", default)

    def is_conversion_log_enabled(self) -> bool:
        """是否啟用轉換日誌"""
        default = self._config.get("logging", {}).get("enable_conversion_log", True)
        return self._get_env_value("DATA_AGENT_LOGGING_CONVERSION_LOG", default)

    def is_performance_log_enabled(self) -> bool:
        """是否啟用性能日誌"""
        default = self._config.get("logging", {}).get("enable_performance_log", True)
        return self._get_env_value("DATA_AGENT_LOGGING_PERFORMANCE_LOG", default)

    # === Embedding 配置（意圖分析用） ===
    def get_embedding_model(self) -> str:
        """獲取 Embedding 模型名稱（RAG 意圖匹配用）"""
        default = self._config.get("embedding", {}).get("model", "qwen3-embedding:latest")
        return self._get_env_value("DATA_AGENT_EMBEDDING_MODEL", default)

    def get_embedding_fallback(self) -> str:
        """獲取 Embedding Fallback 模型（內建 fallback）"""
        default = self._config.get("embedding", {}).get("fallback", "nomic-embed-text")
        return self._get_env_value("DATA_AGENT_EMBEDDING_FALLBACK", default)

    def get_embedding_endpoint(self) -> str:
        """獲取 Embedding 端點"""
        default = self._config.get("embedding", {}).get(
            "endpoint", "http://localhost:11434/api/embeddings"
        )
        return self._get_env_value("DATA_AGENT_EMBEDDING_ENDPOINT", default)

    def get_embedding_dimension(self) -> int:
        """獲取 Embedding 維度"""
        default = self._config.get("embedding", {}).get("dimension", 4096)
        return self._get_env_value("DATA_AGENT_EMBEDDING_DIMENSION", default)

    def get_embedding_timeout(self) -> int:
        """獲取 Embedding 超時時間（秒）"""
        default = self._config.get("embedding", {}).get("timeout", 60)
        return self._get_env_value("DATA_AGENT_EMBEDDING_TIMEOUT", default)

    # === Text-to-SQL 配置（SQL 生成用） ===
    def get_text_to_sql_model(self) -> str:
        """獲取 Text-to-SQL 模型名稱"""
        default = self._config.get("text_to_sql", {}).get("model", "mistral-nemo:12b")
        return self._get_env_value("DATA_AGENT_TEXT_TO_SQL_MODEL", default)

    def get_text_to_sql_temperature(self) -> float:
        """獲取 Text-to-SQL 溫度參數"""
        default = self._config.get("text_to_sql", {}).get("temperature", 0.3)
        return self._get_env_value("DATA_AGENT_TEXT_TO_SQL_TEMPERATURE", default)

    def get_text_to_sql_max_tokens(self) -> int:
        """獲取 Text-to-SQL 最大 token 數"""
        default = self._config.get("text_to_sql", {}).get("max_tokens", 2000)
        return self._get_env_value("DATA_AGENT_TEXT_TO_SQL_MAX_TOKENS", default)

    def get_text_to_sql_timeout(self) -> int:
        """獲取 Text-to-SQL 超時時間（秒）"""
        default = self._config.get("text_to_sql", {}).get("timeout", 120)
        return self._get_env_value("DATA_AGENT_TEXT_TO_SQL_TIMEOUT", default)

    def reload(self) -> None:
        """重新加載配置文件"""
        self._load_config()
        logger.info("配置文件已重新加載")

    def get_config(self) -> Dict[str, Any]:
        """獲取完整配置"""
        return self._config.copy()


# 全局配置實例
_global_config: Optional[DataAgentConfig] = None


def get_config() -> DataAgentConfig:
    """獲取全局配置實例"""
    global _global_config
    if _global_config is None:
        _global_config = DataAgentConfig()
    return _global_config
