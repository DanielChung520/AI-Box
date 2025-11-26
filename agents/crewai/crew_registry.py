# 代碼功能說明: Crew 註冊表實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""實現隊伍註冊表，管理所有 Crew 實例。"""

import logging
from typing import Dict, List, Optional
from datetime import datetime

from agents.crewai.models import CrewConfig, CrewMetrics, CrewRegistryEntry

logger = logging.getLogger(__name__)


class CrewRegistry:
    """隊伍註冊表。"""

    def __init__(self):
        """初始化隊伍註冊表。"""
        self._crews: Dict[str, CrewRegistryEntry] = {}

    def register(
        self,
        crew_id: str,
        config: CrewConfig,
        metrics: Optional[CrewMetrics] = None,
    ) -> bool:
        """
        註冊隊伍。

        Args:
            crew_id: 隊伍 ID
            config: 隊伍配置
            metrics: 觀測指標（可選）

        Returns:
            是否成功註冊
        """
        try:
            if crew_id in self._crews:
                logger.warning(f"Crew '{crew_id}' already registered, updating...")
                entry = self._crews[crew_id]
                entry.config = config
                entry.updated_at = datetime.now()
            else:
                if metrics is None:
                    metrics = CrewMetrics(crew_id=crew_id)
                entry = CrewRegistryEntry(
                    crew_id=crew_id,
                    config=config,
                    metrics=metrics,
                )
                self._crews[crew_id] = entry

            logger.info(f"Registered crew: {crew_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to register crew '{crew_id}': {e}")
            return False

    def unregister(self, crew_id: str) -> bool:
        """
        取消註冊隊伍。

        Args:
            crew_id: 隊伍 ID

        Returns:
            是否成功取消註冊
        """
        try:
            if crew_id not in self._crews:
                logger.warning(f"Crew '{crew_id}' not found")
                return False

            del self._crews[crew_id]
            logger.info(f"Unregistered crew: {crew_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to unregister crew '{crew_id}': {e}")
            return False

    def get(self, crew_id: str) -> Optional[CrewRegistryEntry]:
        """
        獲取隊伍。

        Args:
            crew_id: 隊伍 ID

        Returns:
            隊伍註冊表條目，如果不存在則返回 None
        """
        return self._crews.get(crew_id)

    def list_crews(self) -> List[CrewRegistryEntry]:
        """
        列出所有隊伍。

        Returns:
            隊伍列表
        """
        return list(self._crews.values())

    def update_metrics(
        self,
        crew_id: str,
        metrics: CrewMetrics,
    ) -> bool:
        """
        更新觀測指標。

        Args:
            crew_id: 隊伍 ID
            metrics: 觀測指標

        Returns:
            是否成功更新
        """
        try:
            if crew_id not in self._crews:
                logger.warning(f"Crew '{crew_id}' not found")
                return False

            entry = self._crews[crew_id]
            entry.metrics = metrics
            entry.updated_at = datetime.now()
            logger.info(f"Updated metrics for crew: {crew_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to update metrics for crew '{crew_id}': {e}")
            return False

    def get_crew_count(self) -> int:
        """
        獲取隊伍數量。

        Returns:
            隊伍數量
        """
        return len(self._crews)
