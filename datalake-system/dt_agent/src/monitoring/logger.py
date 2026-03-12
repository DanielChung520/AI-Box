# 代碼功能說明: DT-Agent 日誌模組 — 提供統一的 structlog 日誌配置
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

"""DT-Agent 日誌模組

提供統一的日誌取得方式，各模組透過此模組取得 logger：

    from dt_agent.src.monitoring.logger import get_logger

    logger = get_logger(__name__)
    logger.info("DT-Agent started", component="api")
"""

import logging
from typing import Optional

import structlog


def get_logger(name: Optional[str] = None) -> structlog.stdlib.BoundLogger:
    """取得 structlog logger

    Args:
        name: Logger 名稱（通常使用 __name__）

    Returns:
        structlog BoundLogger 實例
    """
    return structlog.get_logger(name or __name__)


def setup_logging(log_level: str = "INFO") -> None:
    """設置基本日誌配置

    Args:
        log_level: 日誌等級（DEBUG, INFO, WARNING, ERROR）
    """
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )
