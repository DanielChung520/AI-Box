from __future__ import annotations
# 代碼功能說明: Qdrant 客戶端封裝
# 創建日期: 2026-01-23
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24 19:50 UTC+8

"""Qdrant 客戶端封裝，提供連線管理和單例模式。"""


import os
from typing import Optional

import logging
from qdrant_client import QdrantClient

logger = logging.getLogger(__name__)

# 全局 Qdrant 客戶端實例
_qdrant_client: Optional[QdrantClient] = None


def get_qdrant_client() -> QdrantClient:
    """獲取 Qdrant 客戶端實例（單例模式）。

    Returns:
        Qdrant 客戶端實例

    Raises:
        RuntimeError: 如果 Qdrant 連接失敗
    """
    global _qdrant_client

    if _qdrant_client is None:
        # 從配置文件或環境變數獲取配置
        from system.infra.config.config import get_config_section

        datastores_config = get_config_section("datastores", default={}) or {}
        qdrant_config = datastores_config.get("qdrant", {}) if datastores_config else {}

        host = qdrant_config.get("host") or os.getenv("QDRANT_HOST", "localhost")
        port = qdrant_config.get("port") or int(os.getenv("QDRANT_PORT", "6333"))
        api_key = qdrant_config.get("api_key") or os.getenv("QDRANT_API_KEY")
        timeout = qdrant_config.get("timeout", 30)

        if api_key:
            _qdrant_client = QdrantClient(
                host=host,
                port=port,
                api_key=api_key,
                timeout=timeout,
            )
        else:
            _qdrant_client = QdrantClient(
                host=host,
                port=port,
                timeout=timeout,
            )

        # 測試連接
        try:
            collections = _qdrant_client.get_collections()
            logger.info(f"Qdrant connection established: host={host}, port={port}, collections_count={len(collections.collections)}")
        except Exception as e:
            logger.error(f"Qdrant connection failed: error={str(e)}")
            raise RuntimeError(f"Failed to connect to Qdrant: {e}") from e

    return _qdrant_client


def reset_qdrant_client() -> None:
    """重置 Qdrant 客戶端實例（主要用於測試）。"""
    global _qdrant_client
    _qdrant_client = None