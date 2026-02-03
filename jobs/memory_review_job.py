#!/usr/bin/env python3
# 代碼功能說明: AAM 記憶定期檢討 Job
# 創建日期: 2026-02-02
# 創建人: OpenCode AI
# 最後修改日期: 2026-02-02

"""
AAM 記憶定期檢討 Job

功能:
- 每週執行一次低熱度記憶歸檔
- 查找長期未更新但持續訪問的記憶（可能過時）
- 記錄檢討日誌，供後續分析
- 產出用戶記憶健康報告
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from agents.infra.memory.aam.qdrant_adapter import QdrantAdapter

logger = logging.getLogger(__name__)


class MemoryReviewReport:
    """記憶檢討報告"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.generated_at = datetime.now()
        self.low_hotness_count = 0
        self.potentially_stale_count = 0
        self.archived_count = 0
        self.review_count = 0
        self.suggestions: List[str] = []
        self.stats: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at.isoformat(),
            "low_hotness_count": self.low_hotness_count,
            "potentially_stale_count": self.potentially_stale_count,
            "archived_count": self.archived_count,
            "review_count": self.review_count,
            "suggestions": self.suggestions,
            "stats": self.stats,
        }


class MemoryReviewJob:
    """記憶定期檢討 Job"""

    def __init__(
        self,
        adapter: Optional[QdrantAdapter] = None,
        archive_after_days: int = 90,
        max_access_threshold: int = 3,
        stale_check_days: int = 180,
    ):
        """
        初始化檢討 Job

        Args:
            adapter: QdrantAdapter 實例
            archive_after_days: 多少天後歸檔低熱度記憶
            max_access_threshold: 最大訪問次數閾值
            stale_check_days: 檢查多少天前可能過時的記憶
        """
        self.adapter = adapter or QdrantAdapter()
        self.archive_after_days = archive_after_days
        self.max_access_threshold = max_access_threshold
        self.stale_check_days = stale_check_days

    async def run_weekly_review(self) -> List[MemoryReviewReport]:
        """
        執行每週檢討

        Returns:
            檢討報告列表
        """
        logger.info("[AAM REVIEW] 開始執行每週記憶檢討")
        reports = []

        try:
            all_users = await self._get_all_user_ids()

            if not all_users:
                logger.info("[AAM REVIEW] 沒有找到用戶數據")
                return reports

            logger.info(f"[AAM REVIEW] 找到 {len(all_users)} 個用戶")

            for user_id in all_users:
                report = await self._review_user_memory(user_id)
                reports.append(report)

                # 記錄日誌
                logger.info(
                    f"[AAM REVIEW] 用戶 {user_id}: "
                    f"歸檔 {report.archived_count}, "
                    f"待審核 {report.review_count}, "
                    f"低熱度 {report.low_hotness_count}"
                )

            # 產出總結報告
            total_archived = sum(r.archived_count for r in reports)
            total_review = sum(r.review_count for r in reports)
            total_users = len(reports)

            logger.info(
                f"[AAM REVIEW] 檢討完成: "
                f"{total_users} 個用戶, "
                f"歸檔 {total_archived} 筆, "
                f"待審核 {total_review} 筆"
            )

            return reports

        except Exception as e:
            logger.error(f"[AAM REVIEW] 執行失敗: {e}", exc_info=True)
            return reports

    async def _get_all_user_ids(self) -> List[str]:
        """獲取所有用戶 ID"""
        try:
            # 從 Qdrant 獲取所有用戶
            # 這是一個簡化實現，實際應該維護用戶列表
            from agents.infra.memory.aam.models import MemoryType

            all_memories = self.adapter.get_user_entities(
                user_id="",  # 獲取所有用戶
                limit=10000,
            )

            user_ids = set()
            for memory in all_memories:
                if memory.user_id:
                    user_ids.add(memory.user_id)

            return list(user_ids)

        except Exception as e:
            logger.error(f"獲取用戶列表失敗: {e}")
            return []

    async def _review_user_memory(self, user_id: str) -> MemoryReviewReport:
        """
        檢討單個用戶的記憶

        Args:
            user_id: 用戶 ID

        Returns:
            檢討報告
        """
        report = MemoryReviewReport(user_id)

        try:
            # 1. 獲取用戶統計
            stats = self.adapter.get_user_stats(user_id)
            report.stats = stats

            # 2. 查找低熱度記憶
            low_hotness = self.adapter.find_low_hotness(
                user_id=user_id,
                max_access=self.max_access_threshold,
                older_than_days=self.archive_after_days,
            )
            report.low_hotness_count = len(low_hotness)

            # 3. 歸檔低熱度記憶
            for memory in low_hotness:
                success = self.adapter.archive_memory(memory.memory_id)
                if success:
                    report.archived_count += 1
                    logger.info(
                        f"[AAM REVIEW] 歸檔記憶: user={user_id}, "
                        f"memory={memory.memory_id}, "
                        f"access_count={memory.access_count}"
                    )

            # 4. 查找可能過時的記憶（長期未更新但持續訪問）
            potentially_stale = await self._find_potentially_stale(
                user_id=user_id,
                days=self.stale_check_days,
            )
            report.potentially_stale_count = len(potentially_stale)

            # 5. 標記需要人工審核
            for memory in potentially_stale:
                reason = (
                    f"該記憶已存在 {self.stale_check_days} 天，"
                    f"但仍在被訪問（access_count={memory.access_count}），"
                    f"請確認是否仍有效。"
                )
                success = self.adapter.mark_for_review(memory.memory_id, reason)
                if success:
                    report.review_count += 1
                    logger.info(
                        f"[AAM REVIEW] 標記待審核: user={user_id}, "
                        f"memory={memory.memory_id}, "
                        f"reason={reason[:50]}..."
                    )

            # 6. 生成建議
            if report.archived_count > 0:
                report.suggestions.append(
                    f"已歸檔 {report.archived_count} 個低熱度記憶"
                )

            if report.review_count > 0:
                report.suggestions.append(
                    f"有 {report.review_count} 個記憶需要人工審核是否過時"
                )

            if stats.get("total_count", 0) > 1000:
                report.suggestions.append(
                    f"用戶記憶數量較多（{stats['total_count']}），"
                    f"建議定期清理低價值記憶"
                )

            return report

        except Exception as e:
            logger.error(f"檢討用戶記憶失敗: user={user_id}, error={e}", exc_info=True)
            return report

    async def _find_potentially_stale(
        self,
        user_id: str,
        days: int,
    ) -> List[Any]:
        """
        查找可能過時的記憶

        定義：長期未更新（> days）但持續被訪問（access_count > 0）

        Args:
            user_id: 用戶 ID
            days: 天數閾值

        Returns:
            可能過時的記憶列表
        """
        try:
            from datetime import datetime, timedelta
            from agents.infra.memory.aam.models import MemoryType

            cutoff_date = datetime.now() - timedelta(days=days)

            # 獲取該時段前創建的記憶
            all_memories = self.adapter.get_user_entities(
                user_id=user_id,
                status="active",
                limit=1000,
            )

            stale_memories = []
            for memory in all_memories:
                # 檢查是否長期未更新
                if memory.updated_at and memory.updated_at < cutoff_date:
                    # 但有被訪問過
                    if memory.access_count > 0:
                        stale_memories.append(memory)

            return stale_memories

        except Exception as e:
            logger.error(f"查找可能過時記憶失敗: {e}")
            return []

    def run_weekly_review_sync(self) -> List[MemoryReviewReport]:
        """同步執行每週檢討（用於 cron job）"""
        return asyncio.run(self.run_weekly_review())


def run_review_job():
    """運行檢討 Job 的入口函數（用於 cron job）"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    job = MemoryReviewJob()
    reports = job.run_weekly_review_sync()

    # 輸出簡單總結
    total_users = len(reports)
    total_archived = sum(r.archived_count for r in reports)
    total_review = sum(r.review_count for r in reports)

    print(f"\n{'='*60}")
    print(f"AAM 記憶定期檢討完成")
    print(f"{'='*60}")
    print(f"檢討用戶數: {total_users}")
    print(f"歸檔記憶數: {total_archived}")
    print(f"待審核數: {total_review}")
    print(f"{'='*60}\n")

    return reports


if __name__ == "__main__":
    run_review_job()
