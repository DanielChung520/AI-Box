"""
代碼功能說明: 系統日誌配置模組
創建日期: 2025-12-08
創建人: Daniel Chung
最後修改日期: 2025-12-08 12:30:00 UTC+8

功能說明:
- 配置 FastAPI、前端和 MCP Server 的日誌文件
- 使用 RotatingFileHandler 實現日誌輪轉
- 每個日誌文件最大 500KB，保留 4 個備份文件
"""

import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# 日誌目錄
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# 日誌文件路徑
FASTAPI_LOG_PATH = LOG_DIR / "fastapi.log"
FRONTEND_LOG_PATH = LOG_DIR / "frontend.log"
MCP_SERVER_LOG_PATH = LOG_DIR / "mcp_server.log"

# 日誌格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 日誌級別（從環境變量讀取，默認為 INFO）
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()


def setup_file_logger(
    name: str,
    log_file: Path,
    max_bytes: int = 500 * 1024,  # 500KB
    backup_count: int = 4,
    level: str = LOG_LEVEL,
) -> logging.Logger:
    """
    設置文件日誌記錄器

    Args:
        name: 日誌記錄器名稱
        log_file: 日誌文件路徑
        max_bytes: 日誌文件最大大小（字節），默認 500KB
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
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    # 添加處理器
    logger.addHandler(handler)

    # 防止日誌向上傳播到根記錄器
    logger.propagate = False

    return logger


def setup_fastapi_logging() -> None:
    """設置 FastAPI 日誌配置"""
    # 創建 RotatingFileHandler
    handler = RotatingFileHandler(
        FASTAPI_LOG_PATH,
        maxBytes=500 * 1024,  # 500KB
        backupCount=4,
        encoding="utf-8",
    )
    handler.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    handler.setFormatter(formatter)

    # 配置根日誌記錄器（用於 FastAPI 和 uvicorn）
    # 注意：不清除現有處理器，只添加文件處理器，保留控制台輸出
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # 檢查是否已經有文件處理器，避免重複添加
    has_file_handler = any(
        isinstance(h, RotatingFileHandler) and h.baseFilename == str(FASTAPI_LOG_PATH)
        for h in root_logger.handlers
    )

    if not has_file_handler:
        root_logger.addHandler(handler)

    # 同時配置 uvicorn 和 api 相關的日誌記錄器
    for logger_name in ["uvicorn", "uvicorn.access", "uvicorn.error", "api"]:
        logger = logging.getLogger(logger_name)
        logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

        # 檢查是否已經有文件處理器
        has_file_handler = any(
            isinstance(h, RotatingFileHandler)
            and h.baseFilename == str(FASTAPI_LOG_PATH)
            for h in logger.handlers
        )

        if not has_file_handler:
            logger.addHandler(handler)

        # 允許日誌向上傳播到根記錄器（保留 uvicorn 的默認行為）
        logger.propagate = True


def setup_frontend_logging() -> logging.Logger:
    """設置前端日誌配置"""
    return setup_file_logger(
        "frontend",
        FRONTEND_LOG_PATH,
        max_bytes=500 * 1024,  # 500KB
        backup_count=4,
    )


def setup_mcp_server_logging() -> logging.Logger:
    """設置 MCP Server 日誌配置"""
    return setup_file_logger(
        "mcp_server",
        MCP_SERVER_LOG_PATH,
        max_bytes=500 * 1024,  # 500KB
        backup_count=4,
    )


def get_logger(name: str) -> logging.Logger:
    """
    獲取日誌記錄器（如果不存在則創建）

    Args:
        name: 日誌記錄器名稱

    Returns:
        日誌記錄器實例
    """
    return logging.getLogger(name)
