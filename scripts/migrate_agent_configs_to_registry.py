"""
代碼功能說明: 將 agent_display_configs 中的 Agent 技術配置遷移到 system_agent_registry
創建日期: 2026-01-15 02:50 UTC+8
創建人: Daniel Chung
最後修改日期: 2026-01-15 02:50 UTC+8
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# 顯式加載 .env 文件
from dotenv import load_dotenv

env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

from agents.services.registry.models import (
    AgentEndpoints,
    AgentMetadata,
    AgentPermissionConfig,
    AgentRegistryInfo,
    AgentServiceProtocolType,
    AgentStatus,
)
from agents.services.registry.registry import get_agent_registry
from database.arangodb import ArangoDBClient


def migrate_agent_configs() -> None:
    """遷移 Agent 配置到 system_agent_registry"""
    try:
        client = ArangoDBClient()
        if not client.db:
            raise RuntimeError("ArangoDB connection failed")

        # 讀取 agent_display_configs
        display_configs = client.db.collection("agent_display_configs")
        registry = get_agent_registry()

        migrated_count = 0
        skipped_count = 0

        # 遍歷所有展示配置
        for doc in display_configs.all():
            config_type = doc.get("config_type")
            if config_type != "agent":
                continue

            agent_config = doc.get("agent_config", {})
            agent_id = agent_config.get("agent_id") or agent_config.get("id")

            if not agent_id:
                print(f"⚠️ 跳過：缺少 agent_id - {doc.get('_key')}")
                skipped_count += 1
                continue

            # 檢查是否有技術配置字段
            endpoint_url = agent_config.get("endpoint_url")
            protocol = agent_config.get("protocol", "http")
            agent_type = agent_config.get("agent_type", "execution")

            if not endpoint_url:
                print(f"⚠️ 跳過：Agent {agent_id} 沒有 endpoint_url")
                skipped_count += 1
                continue

            # 構建 AgentRegistryInfo
            name_obj = agent_config.get("name", {})
            if isinstance(name_obj, dict):
                name = name_obj.get("zh_TW") or name_obj.get("en") or agent_id
            else:
                name = str(name_obj) if name_obj else agent_id

            desc_obj = agent_config.get("description", {})
            if isinstance(desc_obj, dict):
                description = desc_obj.get("zh_TW") or desc_obj.get("en") or ""
            else:
                description = str(desc_obj) if desc_obj else ""

            status = agent_config.get("status", "offline")
            agent_status = AgentStatus.ONLINE if status == "online" else AgentStatus.OFFLINE

            agent_info = AgentRegistryInfo(
                agent_id=agent_id,
                agent_type=agent_type,
                name=name,
                description=description,
                endpoints=AgentEndpoints(
                    http=endpoint_url if protocol == "http" else None,
                    mcp=endpoint_url if protocol == "mcp" else None,
                    protocol=(
                        AgentServiceProtocolType.MCP
                        if protocol == "mcp"
                        else AgentServiceProtocolType.HTTP
                    ),
                    is_internal=False,
                ),
                capabilities=agent_config.get("capabilities") or [],
                status=agent_status,
                metadata=AgentMetadata(
                    version="1.0.0",
                    tags=[],
                    category=agent_config.get("category_id") or "general",
                ),
                permissions=AgentPermissionConfig(
                    secret_id=agent_config.get("secret_id"),
                    api_key=agent_config.get("secret_key"),
                    allowed_users=[],
                    allowed_tenants=[],
                ),
                is_system_agent=False,
            )

            # 註冊到 Agent Registry
            try:
                registry.register_agent(agent_info)
                print(f"✅ 已遷移：{agent_id} ({name}) - {protocol}://{endpoint_url}")
                migrated_count += 1
            except Exception as reg_exc:
                print(f"❌ 註冊失敗：{agent_id} - {reg_exc}")
                skipped_count += 1

        print("\n📊 遷移統計：")
        print(f"   成功遷移: {migrated_count}")
        print(f"   跳過: {skipped_count}")
        print(f"   總計: {migrated_count + skipped_count}")

    except Exception as exc:
        print(f"❌ 遷移失敗: {exc}")
        import traceback

        traceback.print_exc()
        raise


if __name__ == "__main__":
    migrate_agent_configs()
