# 代碼功能說明: 將 Agent 狀態更新為 online
# 創建日期: 2026-02-03
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-03

"""將 Agent 狀態更新為 online"""

from __future__ import annotations

import sys
from pathlib import Path

# 確保專案根目錄在 sys.path
project_root = Path(__file__).resolve().parent  # scripts 目錄
project_root = project_root.parent  # ai-box 專案根目錄
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

load_dotenv(dotenv_path=project_root / ".env")

import logging
from services.api.services.agent_display_config_store_service import (
    AgentDisplayConfigStoreService,
)
from services.api.models.agent_display_config import AgentConfig

logger = logging.getLogger(__name__)


def update_agent_status_to_online(agent_id: str) -> bool:
    """將 Agent 狀態更新為 online

    Args:
        agent_id: Agent ID

    Returns:
        是否更新成功
    """
    try:
        store = AgentDisplayConfigStoreService()
    except RuntimeError as e:
        logger.error(f"ArangoDB 連線失敗: {e}")
        return False

    tenant_id = None  # 系統級配置

    # 獲取當前 Agent 配置
    # 直接從 collection 獲取配置
    from services.api.services.agent_display_config_store_service import (
        _generate_config_key,
    )

    config_key = _generate_config_key("agent", agent_id=agent_id, tenant_id=tenant_id)
    doc = store._collection.get(config_key)

    if doc is None:
        logger.error(f"找不到 Agent: {agent_id}")
        return False

    # 讀取現有配置
    current_config = AgentConfig(**doc["agent_config"])

    logger.info(f"當前 Agent 狀態: {current_config.status}")

    # 更新狀態為 online
    current_config.status = "online"

    # 更新配置
    success = store.update_agent(
        agent_id=agent_id,
        agent_config=current_config,
        tenant_id=tenant_id,
        updated_by="admin",
    )

    if success:
        logger.info(f"✅ Agent 狀態已更新為 online: {agent_id}")
    else:
        logger.error(f"❌ Agent 狀態更新失敗: {agent_id}")

    return success


def main() -> int:
    """主程式"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 經寶物料管理代理的 ID
    agent_id = "-h0tjyh"

    logger.info(f"開始更新 Agent 狀態: {agent_id}")

    success = update_agent_status_to_online(agent_id)

    if success:
        logger.info("Agent 狀態更新完成")
        return 0

    logger.error("Agent 狀態更新失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
