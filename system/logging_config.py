"""
代碼功能說明: 系統日誌配置模組 — structlog + dictConfig 統一架構
創建日期: 2025-12-08
創建人: Daniel Chung
最後修改日期: 2026-03-04

功能說明:
- 使用 logging.config.dictConfig() 配置 6 個日誌頻道 (system, worker, vectorization,
  graph_extraction, agent_management, ka_agent)
- 使用 structlog.configure() 讓 structlog.get_logger() 與 logging.getLogger() 共用同一 pipeline
- ProcessorFormatter 作為 stdlib ↔ structlog 的橋樑
- 每個 RotatingFileHandler 最大 5MB，保留 5 個備份文件
- setup_mcp_server_logging() 與 setup_frontend_logging() 保持獨立（服務於不同 port）
"""

import logging
import logging.config
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import structlog

# 日誌目錄
LOG_DIR = Path(__file__).parent.parent / "logs"
os.makedirs(str(LOG_DIR), exist_ok=True)

# 日誌級別（從環境變量讀取，默認為 INFO）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# 獨立服務的日誌文件路徑（供 setup_mcp_server_logging / setup_frontend_logging 使用）
FRONTEND_LOG_PATH = LOG_DIR / "frontend.log"
MCP_SERVER_LOG_PATH = LOG_DIR / "mcp_server.log"

# ---------------------------------------------------------------------------
# foreign_pre_chain: 處理 stdlib logging.getLogger() 發出的 LogRecord
# ---------------------------------------------------------------------------
_foreign_pre_chain = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.stdlib.ExtraAdder(),
]

# ---------------------------------------------------------------------------
# dictConfig 配置字典
# ---------------------------------------------------------------------------
_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    # ------------------------------------------------------------------
    # Formatters
    # ------------------------------------------------------------------
    "formatters": {
        "console": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.dev.ConsoleRenderer(colors=True),
            ],
            "foreign_pre_chain": _foreign_pre_chain,
        },
        "json_file": {
            "()": structlog.stdlib.ProcessorFormatter,
            "processors": [
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.JSONRenderer(),
            ],
            "foreign_pre_chain": _foreign_pre_chain,
        },
    },
    # ------------------------------------------------------------------
    # Handlers (1 console + 6 file, all files: 5 MB × 5 backups)
    # ------------------------------------------------------------------
    "handlers": {
        "console_handler": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "console",
            "stream": "ext://sys.stdout",
        },
        "system_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "system.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "worker_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "worker.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "vectorization_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "vectorization.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "graph_extraction_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "graph_extraction.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "agent_management_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "agent_management.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "ka_agent_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json_file",
            "filename": str(LOG_DIR / "ka_agent.log"),
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        },
    },
    # ------------------------------------------------------------------
    # Loggers: root + 5 domain groups + ka_agent
    # ------------------------------------------------------------------
    "loggers": {
        # --- Worker domain ---
        "workers": {
            "level": "DEBUG",
            "handlers": ["console_handler", "worker_file"],
            "propagate": False,
        },
        "database.rq": {
            "level": "DEBUG",
            "handlers": ["console_handler", "worker_file"],
            "propagate": False,
        },
        "services.api.tasks": {
            "level": "DEBUG",
            "handlers": ["console_handler", "worker_file"],
            "propagate": False,
        },
        # --- Vectorization domain ---
        "database.chromadb": {
            "level": "DEBUG",
            "handlers": ["console_handler", "vectorization_file"],
            "propagate": False,
        },
        "database.qdrant": {
            "level": "DEBUG",
            "handlers": ["console_handler", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.embedding_service": {
            "level": "DEBUG",
            "handlers": ["console_handler", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.vector_store_service": {
            "level": "DEBUG",
            "handlers": ["console_handler", "vectorization_file"],
            "propagate": False,
        },
        "services.api.services.qdrant_vector_store_service": {
            "level": "DEBUG",
            "handlers": ["console_handler", "vectorization_file"],
            "propagate": False,
        },
        # --- Graph Extraction domain ---
        "kag": {
            "level": "DEBUG",
            "handlers": ["console_handler", "graph_extraction_file"],
            "propagate": False,
        },
        "database.arangodb": {
            "level": "DEBUG",
            "handlers": ["console_handler", "graph_extraction_file"],
            "propagate": False,
        },
        "agents.builtin.knowledge_ontology_agent": {
            "level": "DEBUG",
            "handlers": ["console_handler", "graph_extraction_file"],
            "propagate": False,
        },
        "services.api.services.kg_extraction_service": {
            "level": "DEBUG",
            "handlers": ["console_handler", "graph_extraction_file"],
            "propagate": False,
        },
        "genai.api.services.kg_builder_service": {
            "level": "DEBUG",
            "handlers": ["console_handler", "graph_extraction_file"],
            "propagate": False,
        },
        # --- Agent Management domain ---
        "agents.orchestrator": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        "agents.builtin.orchestrator_manager": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        "agents.builtin.registry_manager": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        "agents.builtin.moe_agent": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        "agents.services.registry": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        "llm.moe": {
            "level": "DEBUG",
            "handlers": ["console_handler", "agent_management_file"],
            "propagate": False,
        },
        # --- KA-Agent domain ---
        "agents.builtin.ka_agent": {
            "level": "DEBUG",
            "handlers": ["console_handler", "ka_agent_file"],
            "propagate": False,
        },
    },
    # ------------------------------------------------------------------
    # Root logger: catches everything not matched by domain loggers
    # ------------------------------------------------------------------
    "root": {
        "level": LOG_LEVEL,
        "handlers": ["console_handler", "system_file"],
    },
}


def setup_logging() -> None:
    """
    初始化統一日誌系統。

    呼叫順序嚴格：dictConfig FIRST → structlog.configure() SECOND。
    所有 port 8000 的模組共用此配置；MCP Server 與 Frontend 使用各自獨立的函式。
    """
    # Step 1: 配置 stdlib logging
    logging.config.dictConfig(_LOGGING_CONFIG)

    # Step 2: 配置 structlog（使用 stdlib LoggerFactory，共用 dictConfig 的 handlers）
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


# ---------------------------------------------------------------------------
# 獨立服務日誌（保持原有 imperative 風格，不受 dictConfig 管轄）
# ---------------------------------------------------------------------------


def setup_file_logger(
    name: str,
    log_file: Path,
    max_bytes: int = 512 * 1024,  # 512KB
    backup_count: int = 4,
    level: str = LOG_LEVEL,
) -> logging.Logger:
    """
    設置文件日誌記錄器

    Args:
        name: 日誌記錄器名稱
        log_file: 日誌文件路徑
        max_bytes: 日誌文件最大大小（字節），默認 512KB
        backup_count: 保留的備份文件數量，默認 4
        level: 日誌級別，默認從環境變量讀取

    Returns:
        配置好的日誌記錄器
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))

    # 清除現有的處理器（避免重複添加）
    logger.handlers.clear()

    # 創建 RotatingFileHandler
    handler = RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(getattr(logging, level, logging.INFO))

    # 設置日誌格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(log_format, datefmt=date_format)
    handler.setFormatter(formatter)

    # 添加處理器
    logger.addHandler(handler)

    # 防止日誌向上傳播到根記錄器
    logger.propagate = False

    return logger


def setup_frontend_logging() -> logging.Logger:
    """設置前端日誌配置"""
    return setup_file_logger(
        "frontend",
        FRONTEND_LOG_PATH,
        max_bytes=512 * 1024,  # 512KB
        backup_count=4,
    )


def setup_mcp_server_logging() -> logging.Logger:
    """設置 MCP Server 日誌配置"""
    return setup_file_logger(
        "mcp_server",
        MCP_SERVER_LOG_PATH,
        max_bytes=512 * 1024,  # 512KB
        backup_count=4,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    獲取 structlog 日誌記錄器

    Args:
        name: 日誌記錄器名稱

    Returns:
        structlog BoundLogger 實例
    """
    return structlog.get_logger(name)
