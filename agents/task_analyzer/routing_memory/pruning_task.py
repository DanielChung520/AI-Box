# 代碼功能說明: 記憶裁剪後台任務
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""記憶裁剪後台任務 - 定期執行記憶裁剪"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from agents.task_analyzer.routing_memory.pruning import PruningService

# 加載環境變數
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# 默認配置
DEFAULT_INTERVAL_HOURS = 24  # 默認執行間隔：24 小時（每天一次）


class PruningTask:
    """記憶裁剪後台任務類"""

    def __init__(
        self,
        interval_hours: int = DEFAULT_INTERVAL_HOURS,
        ttl_days: int = 90,
        min_frequency: float = 0.01,
        min_success_rate: float = 0.3,
    ):
        """
        初始化記憶裁剪任務

        Args:
            interval_hours: 執行間隔（小時）
            ttl_days: TTL 天數
            min_frequency: 最小使用頻率
            min_success_rate: 最小成功率
        """
        self.interval_hours = interval_hours
        self.pruning_service = PruningService(
            ttl_days=ttl_days,
            min_frequency=min_frequency,
            min_success_rate=min_success_rate,
        )
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def run_once(self) -> dict:
        """
        執行一次記憶裁剪

        Returns:
            裁剪統計信息
        """
        logger.info("Running memory pruning task...")
        try:
            stats = await self.pruning_service.prune_all()
            logger.info(f"Memory pruning task completed: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Memory pruning task failed: {e}", exc_info=True)
            return {"error": str(e)}

    async def run_periodically(self) -> None:
        """
        定期執行記憶裁剪任務
        """
        self._running = True
        logger.info(
            f"Starting periodic memory pruning task (interval: {self.interval_hours} hours)"
        )

        while self._running:
            try:
                await self.run_once()
            except Exception as e:
                logger.error(f"Error in periodic pruning task: {e}", exc_info=True)

            # 等待指定間隔
            await asyncio.sleep(self.interval_hours * 3600)

    def start(self) -> None:
        """
        啟動後台任務
        """
        if self._running:
            logger.warning("Pruning task is already running")
            return

        self._task = asyncio.create_task(self.run_periodically())
        logger.info("Memory pruning task started")

    def stop(self) -> None:
        """
        停止後台任務
        """
        if not self._running:
            logger.warning("Pruning task is not running")
            return

        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("Memory pruning task stopped")


# CLI 命令支持
async def main():
    """CLI 入口點"""
    import argparse

    parser = argparse.ArgumentParser(description="Memory Pruning Task")
    parser.add_argument(
        "--once", action="store_true", help="Run once and exit (default: run periodically)"
    )
    parser.add_argument(
        "--interval-hours",
        type=int,
        default=DEFAULT_INTERVAL_HOURS,
        help="Execution interval (hours)",
    )
    parser.add_argument("--ttl-days", type=int, default=90, help="TTL days")
    parser.add_argument(
        "--min-frequency", type=float, default=0.01, help="Minimum frequency threshold"
    )
    parser.add_argument(
        "--min-success-rate", type=float, default=0.3, help="Minimum success rate threshold"
    )

    args = parser.parse_args()

    task = PruningTask(
        interval_hours=args.interval_hours,
        ttl_days=args.ttl_days,
        min_frequency=args.min_frequency,
        min_success_rate=args.min_success_rate,
    )

    if args.once:
        # 執行一次
        stats = await task.run_once()
        print(f"Pruning completed: {stats}")
    else:
        # 定期執行
        try:
            await task.run_periodically()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
            task.stop()


if __name__ == "__main__":
    asyncio.run(main())
