# 代碼功能說明: 品質評估服務
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""品質評估服務

評估 Agent 能力品質，用於優化系統性能。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .execution_record import ExecutionRecordStoreService, get_execution_record_store_service


class AgentQualityScore(BaseModel):
    """Agent 品質評分"""

    agent_id: str = Field(..., description="Agent ID")
    total_executions: int = Field(..., description="總執行次數", ge=0)
    success_rate: float = Field(..., description="成功率（0.0-1.0）", ge=0.0, le=1.0)
    avg_latency_ms: float = Field(..., description="平均延遲時間（毫秒）", ge=0.0)
    user_correction_rate: float = Field(..., description="用戶修正率（0.0-1.0）", ge=0.0, le=1.0)
    quality_score: float = Field(..., description="品質評分（0.0-1.0）", ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, description="額外元數據")


class QualityAssessmentReport(BaseModel):
    """品質評估報告"""

    period_start: datetime = Field(..., description="統計開始時間")
    period_end: datetime = Field(..., description="統計結束時間")
    total_agents: int = Field(..., description="Agent 總數", ge=0)
    total_executions: int = Field(..., description="總執行次數", ge=0)
    overall_quality_score: float = Field(..., description="總體品質評分（0.0-1.0）", ge=0.0, le=1.0)
    agent_scores: List[AgentQualityScore] = Field(
        default_factory=list, description="各 Agent 的品質評分"
    )


class QualityAssessmentService:
    """品質評估服務"""

    def __init__(self, record_store: Optional[ExecutionRecordStoreService] = None) -> None:
        """
        初始化品質評估服務

        Args:
            record_store: 執行記錄存儲服務，如果為 None 則使用全局實例
        """
        self._record_store = record_store or get_execution_record_store_service()

    def calculate_quality_score(
        self,
        success_rate: float,
        avg_latency_ms: float,
        user_correction_rate: float,
        latency_threshold_ms: float = 5000.0,
    ) -> float:
        """
        計算品質評分

        品質評分公式：
        - 基礎分：success_rate（0.0-1.0）
        - 延遲懲罰：如果 avg_latency_ms > latency_threshold_ms，則降低評分
        - 用戶修正懲罰：user_correction_rate 越高，評分越低

        Args:
            success_rate: 成功率（0.0-1.0）
            avg_latency_ms: 平均延遲時間（毫秒）
            user_correction_rate: 用戶修正率（0.0-1.0）
            latency_threshold_ms: 延遲閾值（毫秒），超過此值會降低評分

        Returns:
            品質評分（0.0-1.0）
        """
        # 基礎分：成功率
        base_score = success_rate

        # 延遲懲罰：如果延遲超過閾值，按比例降低評分
        if avg_latency_ms > latency_threshold_ms:
            latency_penalty = min(
                0.3, (avg_latency_ms - latency_threshold_ms) / latency_threshold_ms * 0.3
            )
            base_score = max(0.0, base_score - latency_penalty)

        # 用戶修正懲罰：修正率越高，評分越低
        correction_penalty = user_correction_rate * 0.2
        final_score = max(0.0, base_score - correction_penalty)

        return final_score

    def assess_agent_quality(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AgentQualityScore:
        """
        評估指定 Agent 的品質

        Args:
            agent_id: Agent ID
            start_time: 開始時間（可選，默認為 7 天前）
            end_time: 結束時間（可選，默認為現在）

        Returns:
            Agent 品質評分
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # 查詢記錄
        records = self._record_store.get_records_by_time_range(start_time, end_time, limit=10000)

        # 過濾指定 Agent
        agent_records = [r for r in records if agent_id in r.get("agent_ids", [])]

        if not agent_records:
            return AgentQualityScore(
                agent_id=agent_id,
                total_executions=0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                user_correction_rate=0.0,
                quality_score=0.0,
            )

        total_executions = len(agent_records)
        success_count = sum(1 for r in agent_records if r.get("execution_success", False))
        success_rate = success_count / total_executions if total_executions > 0 else 0.0

        avg_latency_ms = (
            sum(r.get("latency_ms", 0) for r in agent_records) / total_executions
            if total_executions > 0
            else 0.0
        )

        user_correction_count = sum(1 for r in agent_records if r.get("user_correction", False))
        user_correction_rate = (
            user_correction_count / total_executions if total_executions > 0 else 0.0
        )

        quality_score = self.calculate_quality_score(
            success_rate, avg_latency_ms, user_correction_rate
        )

        return AgentQualityScore(
            agent_id=agent_id,
            total_executions=total_executions,
            success_rate=success_rate,
            avg_latency_ms=avg_latency_ms,
            user_correction_rate=user_correction_rate,
            quality_score=quality_score,
            metadata={
                "success_count": success_count,
                "failure_count": total_executions - success_count,
            },
        )

    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> QualityAssessmentReport:
        """
        生成品質評估報告

        Args:
            start_time: 開始時間（可選，默認為 7 天前）
            end_time: 結束時間（可選，默認為現在）

        Returns:
            品質評估報告
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # 查詢記錄
        records = self._record_store.get_records_by_time_range(start_time, end_time, limit=10000)

        if not records:
            return QualityAssessmentReport(
                period_start=start_time,
                period_end=end_time,
                total_agents=0,
                total_executions=0,
                overall_quality_score=0.0,
                agent_scores=[],
            )

        # 按 Agent 分組統計
        agent_groups: Dict[str, List[Dict[str, Any]]] = {}
        for record in records:
            agent_ids = record.get("agent_ids", [])
            for agent_id in agent_ids:
                if agent_id not in agent_groups:
                    agent_groups[agent_id] = []
                agent_groups[agent_id].append(record)

        # 計算各 Agent 的品質評分
        agent_scores: List[AgentQualityScore] = []
        total_executions = len(records)
        total_quality_score = 0.0
        agent_count = 0

        for agent_id in agent_groups.keys():
            score = self.assess_agent_quality(agent_id, start_time, end_time)
            agent_scores.append(score)
            if score.total_executions > 0:
                total_quality_score += score.quality_score
                agent_count += 1

        # 計算總體品質評分
        overall_quality_score = total_quality_score / agent_count if agent_count > 0 else 0.0

        return QualityAssessmentReport(
            period_start=start_time,
            period_end=end_time,
            total_agents=len(agent_groups),
            total_executions=total_executions,
            overall_quality_score=overall_quality_score,
            agent_scores=sorted(agent_scores, key=lambda x: x.quality_score, reverse=True),
        )

    def get_top_agents(
        self,
        top_n: int = 10,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AgentQualityScore]:
        """
        獲取品質評分最高的 Agent 列表

        Args:
            top_n: 返回前 N 個
            start_time: 開始時間（可選）
            end_time: 結束時間（可選）

        Returns:
            Agent 品質評分列表（按品質評分降序）
        """
        report = self.generate_report(start_time, end_time)
        return report.agent_scores[:top_n]


def get_quality_assessment_service() -> QualityAssessmentService:
    """獲取品質評估服務單例"""
    global _quality_assessment_service
    if _quality_assessment_service is None:
        _quality_assessment_service = QualityAssessmentService()
    return _quality_assessment_service


_quality_assessment_service: Optional[QualityAssessmentService] = None
