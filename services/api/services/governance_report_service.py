# 代碼功能說明: AI治理報告服務
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06 15:47 (UTC+8)

"""AI治理報告服務 - 生成AI治理報告"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import structlog

from services.api.services.model_usage_service import get_model_usage_service
from services.api.services.data_quality_service import get_data_quality_service
from services.api.services.bias_detection_service import get_bias_detection_service

logger = structlog.get_logger(__name__)


class GovernanceReportService:
    """AI治理報告服務"""

    def __init__(self):
        """初始化治理報告服務"""
        self.logger = logger
        self.model_usage_service = get_model_usage_service()
        self.data_quality_service = get_data_quality_service()
        self.bias_detection_service = get_bias_detection_service()

    def generate_report(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成AI治理報告

        Args:
            start_time: 開始時間（可選，默認為7天前）
            end_time: 結束時間（可選，默認為現在）
            user_id: 用戶ID（可選）

        Returns:
            治理報告
        """
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(days=7)

        # 獲取模型使用統計
        model_stats = self.model_usage_service.get_stats(
            user_id=user_id, start_time=start_time, end_time=end_time
        )

        # 計算總體指標
        total_calls = sum(stat.total_calls for stat in model_stats)
        total_users = len(set(stat.total_users for stat in model_stats))
        avg_success_rate = (
            sum(stat.success_rate for stat in model_stats) / len(model_stats)
            if model_stats
            else 0.0
        )

        report = {
            "report_period": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
            },
            "model_usage": {
                "total_calls": total_calls,
                "total_users": total_users,
                "avg_success_rate": avg_success_rate,
                "models": [
                    {
                        "model_name": stat.model_name,
                        "total_calls": stat.total_calls,
                        "total_users": stat.total_users,
                        "success_rate": stat.success_rate,
                        "avg_latency_ms": stat.avg_latency_ms,
                        "purposes": stat.purposes,
                    }
                    for stat in model_stats
                ],
            },
            "data_quality": {
                "summary": "數據質量檢查需要針對具體文件進行",
                "note": "使用 /data-quality/check/{file_id} 端點檢查特定文件",
            },
            "bias_detection": {
                "summary": "偏見檢測需要針對具體的NER/RE結果進行",
                "note": "使用偏見檢測服務檢查實體和關係",
            },
            "recommendations": self._generate_recommendations(model_stats),
            "generated_at": datetime.utcnow().isoformat(),
        }

        return report

    def _generate_recommendations(self, model_stats: List[Any]) -> List[str]:
        """
        生成建議

        Args:
            model_stats: 模型使用統計列表

        Returns:
            建議列表
        """
        recommendations: List[str] = []

        if not model_stats:
            recommendations.append("沒有模型使用數據，建議開始使用AI功能")
            return recommendations

        # 檢查成功率
        low_success_models = [stat for stat in model_stats if stat.success_rate < 0.8]
        if low_success_models:
            recommendations.append(
                f"發現 {len(low_success_models)} 個模型的成功率低於80%，建議檢查模型配置和數據質量"
            )

        # 檢查延遲
        high_latency_models = [
            stat for stat in model_stats if stat.avg_latency_ms > 5000
        ]
        if high_latency_models:
            recommendations.append(
                f"發現 {len(high_latency_models)} 個模型的平均延遲超過5秒，建議優化模型或使用更快的模型"
            )

        return recommendations


# 全局服務實例（懶加載）
_governance_report_service: Optional[GovernanceReportService] = None


def get_governance_report_service() -> GovernanceReportService:
    """獲取治理報告服務實例（單例模式）"""
    global _governance_report_service
    if _governance_report_service is None:
        _governance_report_service = GovernanceReportService()
    return _governance_report_service
