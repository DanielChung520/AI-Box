# 代碼功能說明: Tiptop Dashboard 配置
# 創建日期: 2026-01-29
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-29 UTC+8

"""Tiptop Dashboard 配置"""

import os
from pathlib import Path

# 專案根目錄（datalake-system）
DASHBOARD_DIR = Path(__file__).resolve().parent
DATALAKE_ROOT = DASHBOARD_DIR.parent

# Schema 路徑
SCHEMA_REGISTRY_PATH = DATALAKE_ROOT / "metadata" / "schema_registry.json"

# 服務 URL
DATA_AGENT_URL = os.getenv("DATA_AGENT_SERVICE_URL", "http://localhost:8004/execute")
SEAWEEDFS_ENDPOINT = os.getenv("DATALAKE_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8334")
DEFAULT_BUCKET = os.getenv("DATALAKE_DEFAULT_BUCKET", "tiptop-raw")

# Streamlit 端口
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8502"))
