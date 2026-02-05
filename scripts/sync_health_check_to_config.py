#!/usr/bin/env python3
"""
代碼功能說明: LLM Provider 健康檢查狀態同步到簡化模型配置
創建日期: 2026-02-03
創建人: Daniel Chung
最後修改日期: 2026-02-03

定期檢查 LLM provider 健康狀態，並更新 simplified_model_config.json 的 status 字段
"""

import asyncio
import logging
import time
from pathlib import Path

from llm.moe.moe_manager import LLMMoEManager
from services.api.services.simplified_model_service import get_simplified_model_service

logger = logging.getLogger(__name__)


async def sync_health_check_to_config(interval_seconds: int = 60) -> None:
    """
    同步健康檢查結果到簡化模型配置

    Args:
        interval_seconds: 檢查間隔（秒）
    """
    logger.info("Starting health check sync service...")

    simplified_service = get_simplified_model_service()
    moe = LLMMoEManager()

    while True:
        try:
            # 獲取健康檢查結果
            provider_health = {}

            if moe.failover_manager is not None:
                health_results = moe.failover_manager._provider_health

                # 轉換為簡化服務需要的格式
                for provider, health_result in health_results.items():
                    provider_key = provider.value.lower()
                    provider_health[provider_key] = {
                        "healthy": health_result.healthy,
                        "latency": health_result.latency,
                        "error": health_result.error,
                    }

            # 更新模型狀態
            has_changes = simplified_service.update_model_status_from_health_check(provider_health)

            if has_changes:
                logger.info("Model status updated from health check results")

            # 等待下次檢查
            await asyncio.sleep(interval_seconds)

        except asyncio.CancelledError:
            logger.info("Health check sync service stopped")
            break
        except Exception as e:
            logger.error(f"Error in health check sync: {e}", exc_info=True)
            await asyncio.sleep(interval_seconds)


async def manual_sync() -> None:
    """手動執行一次同步（用於測試或腳本調用）"""
    logger.info("Manual health check sync...")
    simplified_service = get_simplified_model_service()
    moe = LLMMoEManager()

    provider_health = {}

    if moe.failover_manager is not None:
        health_results = moe.failover_manager._provider_health

        for provider, health_result in health_results.items():
            provider_key = provider.value.lower()
            provider_health[provider_key] = {
                "healthy": health_result.healthy,
                "latency": health_result.latency,
                "error": health_result.error,
            }

    has_changes = simplified_service.update_model_status_from_health_check(provider_health)

    if has_changes:
        logger.info("Model status updated successfully")
    else:
        logger.info("No changes detected")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    # 手動執行一次
    asyncio.run(manual_sync())
