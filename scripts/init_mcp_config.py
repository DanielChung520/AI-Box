"""
代碼功能說明: 初始化 MCP Gateway 系統配置
創建日期: 2026-01-15 02:42 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-15 02:43 UTC+8
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 顯式加載 .env 文件（AI 開發路徑加載規範）
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

from database.arangodb import ArangoDBClient


def init_mcp_config() -> None:
    """初始化 MCP Gateway 系統配置"""
    try:
        client = ArangoDBClient()
        if not client.db:
            raise RuntimeError("ArangoDB connection failed")

        collection = client.db.collection("system_configs")
        config_key = "mcp_gateway"

        # 檢查配置是否已存在
        existing = collection.get(config_key)
        if existing:
            print(f"✅ MCP Gateway 配置已存在：{existing.get('config_data')}")
            return

        # 創建配置
        now = datetime.utcnow().isoformat()
        doc = {
            "_key": config_key,
            "tenant_id": None,
            "scope": "mcp_gateway",
            "sub_scope": None,
            "is_active": True,
            "config_data": {
                "default_endpoint": "https://mcp.k84.org",
                "description": "MCP Gateway 默認端點配置（正式環境可修改此配置）",
                "protocol": "mcp",
            },
            "metadata": {},
            "created_at": now,
            "updated_at": now,
            "created_by": "system",
            "updated_by": "system",
        }

        collection.insert(doc)

        print("✅ MCP Gateway 系統配置已創建！")
        print(f"   默認端點: {doc['config_data']['default_endpoint']}")
        print(f"   協議: {doc['config_data']['protocol']}")
        print("\n💡 提示：可在 ArangoDB 的 system_configs collection 中修改此配置")
        print("   Collection: system_configs")
        print(f"   Key: {config_key}")

    except Exception as exc:
        print(f"❌ 創建配置失敗: {exc}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    init_mcp_config()
