# 代碼功能說明: 命中率統計服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""命中率統計服務

統計 Intent → Task 命中率，用於評估系統性能。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .execution_record import ExecutionRecordStoreService, get_execution_record_store_service


class HitRateStats(BaseModel):
    """命中率統計結果"""

    intent: str = Field(..., description="Intent 名稱")
    total_count: int = Field(..., description="總執行次數", ge=0)
    success_count: int = Field(..., description="成功次數", ge=0)
    failure_count: int = Field(..., description="失敗次數", ge=0)
    hit_rate: float = Field(..., description="命中率（0.0-1.0）", ge=0.0, le=1.0)
    avg_task_count: float = Field(..., description="平均任務數量", ge=0.0)
    avg_latency_ms: float = Field(..., description="平均延遲時間（毫秒）", ge=0.0)
    user_correction_rate: float = Field(..., description="用戶修正率（0.0-1.0）", ge=0.0, le=1.0)


class HitRateReport(BaseModel):
    """命中率報告"""

    period_start: datetime = Field(..., description="統計開始時間")
    period_end: datetime = Field(..., description="統計結束時間")
    total_intents: int = Field(..., description="Intent 總數", ge=0)
    total_executions: int = Field(..., description="總執行次數", ge=0)
    overall_hit_rate: float = Field(..., description="總體命中率（0.0-1.0）", ge=0.0, le=1.0)
    intent_stats: List[HitRateStats] = Field(
        default_factory=list, description="各 Intent 的統計結果"
    )


class HitRateService:
    """命中率統計服務"""

    def __init__(self, record_store: Optional[ExecutionRecordStoreService] = None) -> None:
        """
        初始化命中率統計服務

        Args:
            record_store: 執行記錄存儲服務，如果為 None 則使用全局實例
        """
        self._record_store = record_store or get_execution_record_store_service()

    def calculate_hit_rate(
        self,
        intent: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> HitRateStats:
        """
        計算指定 Intent 的命中率

        Args:
            intent: Intent 名稱
            start_time: 開始時間（可選，默認為 7 天前）
            end_time: 結束時間（可選，默認為現在）

        Returns:
            命中率統計結果
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # 查詢記錄
        records = self._record_store.get_records_by_time_range(start_time, end_time, limit=10000)

        # 過濾指定 Intent
        intent_records = [r for r in records if r.get("intent") == intent]

        if not intent_records:
            return HitRateStats(
                intent=intent,
                total_count=0,
                success_count=0,
                failure_count=0,
                hit_rate=0.0,
                avg_task_count=0.0,
                avg_latency_ms=0.0,
                user_correction_rate=0.0,
            )

        total_count = len(intent_records)
        success_count = sum(1 for r in intent_records if r.get("execution_success", False))
        failure_count = total_count - success_count
        hit_rate = success_count / total_count if total_count > 0 else 0.0

        avg_task_count = (
            sum(r.get("task_count", 0) for r in intent_records) / total_count
            if total_count > 0
            else 0.0
        )
        avg_latency_ms = (
            sum(r.get("latency_ms", 0) for r in intent_records) / total_count
            if total_count > 0
            else 0.0
        )
        user_correction_count = sum(1 for r in intent_records if r.get("user_correction", False))
        user_correction_rate = user_correction_count / total_count if total_count > 0 else 0.0

        return HitRateStats(
            intent=intent,
            total_count=total_count,
            success_count=success_count,
            failure_count=failure_count,
            hit_rate=hit_rate,
            avg_task_count=avg_task_count,
            avg_latency_ms=avg_latency_ms,
            user_correction_rate=user_correction_rate,
        )

    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> HitRateReport:
        """
        生成命中率報告

        Args:
            start_time: 開始時間（可選，默認為 7 天前）
            end_time: 結束時間（可選，默認為現在）

        Returns:
            命中率報告
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # 查詢記錄
        records = self._record_store.get_records_by_time_range(start_time, end_time, limit=10000)

        if not records:
            return HitRateReport(
                period_start=start_time,
                period_end=end_time,
                total_intents=0,
                total_executions=0,
                overall_hit_rate=0.0,
                intent_stats=[],
            )

        # 按 Intent 分組統計
        intent_groups: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            intent = record.get("intent", "unknown")
            if intent not in intent_groups:
                intent_groups[intent] = []
            intent_groups[intent].append(record)

        # 計算各 Intent 的統計
        intent_stats: List[HitRateStats] = []
        total_executions = len(records)
        total_success = 0

        for intent, intent_records in intent_groups.items():
            stats = self.calculate_hit_rate(intent, start_time, end_time)
            intent_stats.append(stats)
            total_success += stats.success_count

        # 計算總體命中率
        overall_hit_rate = total_success / total_executions if total_executions > 0 else 0.0

        return HitRateReport(
            period_start=start_time,
            period_end=end_time,
            total_intents=len(intent_groups),
            total_executions=total_executions,
            overall_hit_rate=overall_hit_rate,
            intent_stats=sorted(intent_stats, key=lambda x: x.total_count, reverse=True),
        )

    def get_top_intents(
        self,
        top_n: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[HitRateStats]:
        """
        獲取執行次數最多的 Intent 列表

        Args:
            top_n: 返回前 N 個
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）

        Returns:
            命中率統計結果列表（按執行次數降序）
        """
        report = self.generate_report(start_time, end_time)
        return report.intent_stats[:top_n]


def get_hit_rate_service() -> HitRateService:
    """獲取命中率統計服務單例"""
    global _hit_rate_service
    if _hit_rate_service is None:
        _hit_rate_service = HitRateService()
    return _hit_rate_service


_hit_rate_service: Optional[HitRateService] = None
