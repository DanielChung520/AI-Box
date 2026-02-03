#!/usr/bin/env python3
# 代碼功能說明: 手動註冊 KA-Agent 到 System Agent Registry
# 創建日期: 2026-01-28
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""手動註冊 KA-Agent 到 System Agent Registry

此腳本用於手動將 KA-Agent 註冊到 System Agent Registry (ArangoDB) 和 Agent Registry (內存)。

使用方法:
    python register_ka_agent.py
"""

import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def register_ka_agent():
    """註冊 KA-Agent 到 System Agent Registry"""
    try:
        logger.info("=" * 60)
        logger.info("開始註冊 KA-Agent 到 System Agent Registry")
        logger.info("=" * 60)

        # 1. 初始化並註冊所有內建 Agent（包括 KA-Agent）
        logger.info("正在初始化並註冊所有內建 Agent...")
        from agents.builtin import register_builtin_agents

        registered_agents = register_builtin_agents()
        logger.info(f"已註冊 {len(registered_agents)} 個內建 Agent")

        # 2. 檢查 KA-Agent 是否成功註冊
        ka_agent = registered_agents.get("ka_agent")
        if ka_agent:
            logger.info(f"✅ KA-Agent 實例已初始化: {ka_agent.agent_id}")
        else:
            logger.warning("⚠️ KA-Agent 實例未找到，可能初始化失敗")

        # 3. 檢查 System Agent Registry
        logger.info("正在檢查 System Agent Registry...")
        from services.api.services.system_agent_registry_store_service import (
            get_system_agent_registry_store_service,
        )

        system_agent_store = get_system_agent_registry_store_service()
        agent_id = "ka-agent"
        system_agent = system_agent_store.get_system_agent(agent_id)

        if system_agent:
            logger.info(f"✅ KA-Agent ({agent_id}) 已存在於 System Agent Registry")
            logger.info(f"   狀態: {system_agent.status}")
            logger.info(f"   是否啟用: {system_agent.is_active}")
            logger.info(f"   版本: {system_agent.version}")
            logger.info(f"   能力: {system_agent.capabilities}")
        else:
            logger.warning(f"⚠️ KA-Agent ({agent_id}) 未在 System Agent Registry 中找到")
            logger.info("這可能是因為註冊過程中發生錯誤，請檢查日誌")

        # 4. 檢查 Agent Registry (內存)
        logger.info("正在檢查 Agent Registry (內存)...")
        from agents.services.registry.registry import get_agent_registry

        registry = get_agent_registry()
        agent_info = registry.get_agent_info(agent_id)

        if agent_info:
            logger.info(f"✅ KA-Agent ({agent_id}) 已存在於 Agent Registry (內存)")
            logger.info(f"   狀態: {agent_info.status}")
            logger.info(f"   是否為 System Agent: {agent_info.is_system_agent}")
            logger.info(f"   能力: {agent_info.capabilities}")
        else:
            logger.warning(f"⚠️ KA-Agent ({agent_id}) 未在 Agent Registry (內存) 中找到")

        logger.info("=" * 60)
        if system_agent and agent_info:
            logger.info("✅ KA-Agent 註冊完成！")
        else:
            logger.warning("⚠️ KA-Agent 註冊可能未完全成功，請檢查上述日誌")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ 註冊 KA-Agent 時發生錯誤: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    register_ka_agent()
