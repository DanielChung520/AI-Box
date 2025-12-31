# 代碼功能說明: AI治理報告服務（WBS-4.4: 治理報告系統）
# 創建日期: 2025-12-06 15:47 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""AI治理報告服務 - 生成AI治理報告"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog

from services.api.services.bias_detection_service import get_bias_detection_service
from services.api.services.data_quality_service import get_data_quality_service
from services.api.services.model_usage_service import get_model_usage_service

# WBS-4.4: 擴展支持 Ontology/Config 統計
try:
    from services.api.services.config_store_service import get_config_store_service
    from services.api.services.ontology_store_service import get_ontology_store_service

    ONTOLOGY_CONFIG_AVAILABLE = True
except ImportError:
    ONTOLOGY_CONFIG_AVAILABLE = False

logger = structlog.get_logger(__name__)


class GovernanceReportService:
    """AI治理報告服務"""

    def __init__(self):
        """初始化治理報告服務"""
        self.logger = logger
        self.model_usage_service = get_model_usage_service()
        self.data_quality_service = get_data_quality_service()
        self.bias_detection_service = get_bias_detection_service()

        # WBS-4.4: 擴展支持 Ontology/Config
        if ONTOLOGY_CONFIG_AVAILABLE:
            try:
                self.ontology_service = get_ontology_store_service()
                self.config_service = get_config_store_service()
            except Exception:
                self.ontology_service = None  # type: ignore[assignment]  # 允許 None 以支持向後兼容
                self.config_service = None  # type: ignore[assignment]  # 允許 None 以支持向後兼容
        else:
            self.ontology_service = None  # type: ignore[assignment]  # 允許 None 以支持向後兼容
            self.config_service = None  # type: ignore[assignment]  # 允許 None 以支持向後兼容

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

        # WBS-4.4: 添加 Ontology 使用統計
        if self.ontology_service:
            try:
                ontologies = self.ontology_service.list_ontologies(is_active=True)
                report["ontology_usage"] = {
                    "total_ontologies": len(ontologies),
                    "by_type": self._count_ontologies_by_type(ontologies),
                    "by_tenant": self._count_ontologies_by_tenant(ontologies),
                }
            except Exception as e:
                logger.warning("Failed to get ontology statistics", error=str(e))
                report["ontology_usage"] = {"error": "無法獲取 Ontology 統計"}

        # WBS-4.4: 添加 Config 變更統計（需要從審計日誌中獲取）
        report["config_changes"] = {
            "note": "Config 變更統計需要從審計日誌中查詢",
        }

        # WBS-4.2.3: 添加 Ontology 和 Config 品質統計
        report["ontology_config_quality"] = self._generate_ontology_config_quality_summary()

        return report

    def _count_ontologies_by_type(self, ontologies: List[Any]) -> Dict[str, int]:
        """統計 Ontology 按類型分布"""
        counts: Dict[str, int] = {}
        for ontology in ontologies:
            ontology_type = getattr(ontology, "type", "unknown")
            counts[ontology_type] = counts.get(ontology_type, 0) + 1
        return counts

    def _count_ontologies_by_tenant(self, ontologies: List[Any]) -> Dict[str, int]:
        """統計 Ontology 按租戶分布"""
        counts: Dict[str, int] = {}
        for ontology in ontologies:
            tenant_id = getattr(ontology, "tenant_id", "global")
            counts[tenant_id or "global"] = counts.get(tenant_id or "global", 0) + 1
        return counts

    def _generate_ontology_config_quality_summary(self) -> Dict[str, Any]:
        """
        生成 Ontology 和 Config 品質摘要（WBS-4.2.3: 數據品質監控）

        Returns:
            品質摘要報告
        """
        summary: Dict[str, Any] = {
            "ontology_quality": {"note": "使用數據品質服務檢查具體 Ontology"},
            "config_quality": {"note": "使用數據品質服務檢查具體 Config"},
        }

        try:
            # 檢查 Ontology 品質（抽樣檢查，避免性能問題）
            if self.ontology_service:
                ontologies = self.ontology_service.list_ontologies(is_active=True, limit=10)
                if ontologies:
                    ontology_issues = []
                    for ontology in ontologies[:5]:  # 只檢查前5個作為示例
                        issues = self.data_quality_service.check_ontology_quality(
                            ontology, self.ontology_service
                        )
                        ontology_issues.extend(issues)

                    critical_count = sum(
                        1 for issue in ontology_issues if issue.severity == "critical"
                    )
                    warning_count = sum(
                        1 for issue in ontology_issues if issue.severity == "warning"
                    )

                    summary["ontology_quality"] = {
                        "sampled_count": min(5, len(ontologies)),
                        "total_checked": len(ontologies),
                        "critical_issues": critical_count,
                        "warning_issues": warning_count,
                        "note": "這只是抽樣檢查，詳細檢查請使用數據品質服務",
                    }

            # Config 品質檢查（抽樣檢查）
            if self.config_service:
                # 獲取一些系統配置進行檢查
                try:
                    # 這裡只是示例，實際可能需要從審計日誌或其他方式獲取配置列表
                    summary["config_quality"] = {
                        "note": "Config 品質檢查需要具體的 Config ID，請使用數據品質服務進行詳細檢查",
                    }
                except Exception as e:
                    logger.warning("Config 品質檢查失敗", error=str(e))

        except Exception as e:
            logger.warning("生成 Ontology/Config 品質摘要失敗", error=str(e))
            summary["error"] = str(e)

        return summary

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
        high_latency_models = [stat for stat in model_stats if stat.avg_latency_ms > 5000]
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
