# 代碼功能說明: Config Preview Service - 配置預覽服務
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Config Preview Service

配置預覽服務，提供配置變更前的影響分析、成本預估和風險評估。
"""

import logging
from typing import Any, Dict, Optional

from agents.task_analyzer.models import ConfigIntent
from services.api.models.config import ConfigModel

from .models import ConfigPreview

logger = logging.getLogger(__name__)


class ConfigPreviewService:
    """配置預覽服務 - 生成配置變更預覽"""

    def __init__(self):
        """初始化配置預覽服務"""
        self._logger = logger

    async def generate_preview(
        self, intent: ConfigIntent, current_config: Optional[ConfigModel] = None
    ) -> ConfigPreview:
        """
        生成配置變更預覽

        Args:
            intent: 配置操作意圖
            current_config: 當前配置（可選）

        Returns:
            ConfigPreview: 包含影響分析、成本預估、風險評估
        """
        try:
            # 1. 分析影響範圍
            impact = await self._analyze_impact(intent, current_config)

            # 2. 計算成本變化
            cost_change = await self._calculate_cost_change(intent, current_config)

            # 3. 評估風險
            risk_level = await self._assess_risk(intent, current_config)

            # 4. 確定是否需要確認（危險操作需要確認）
            confirmation_required = risk_level in ["high", "medium"]

            return ConfigPreview(
                changes=intent.config_data or {},
                impact_analysis=impact,
                cost_change=cost_change,
                risk_level=risk_level,
                confirmation_required=confirmation_required,
            )

        except Exception as e:
            self._logger.error(f"Failed to generate preview: {e}", exc_info=True)
            # 返回默認預覽（高風險，需要確認）
            return ConfigPreview(
                changes=intent.config_data or {},
                impact_analysis={"error": str(e)},
                cost_change=None,
                risk_level="high",
                confirmation_required=True,
            )

    async def _analyze_impact(
        self, intent: ConfigIntent, current_config: Optional[ConfigModel]
    ) -> Dict[str, Any]:
        """
        分析影響範圍

        Args:
            intent: 配置操作意圖
            current_config: 當前配置

        Returns:
            影響分析結果
        """
        impact = {
            "affected_users": 0,
            "affected_tenants": 0,
            "affected_services": [],
            "configuration_changes": {},
            "estimated_downtime": "none",
        }

        try:
            # 根據配置層級評估影響範圍
            if intent.level == "system":
                impact["affected_users"] = -1  # -1 表示所有用戶
                impact["affected_tenants"] = -1  # -1 表示所有租戶
                impact["affected_services"] = ["all"]
            elif intent.level == "tenant":
                impact["affected_users"] = -1  # 租戶下的所有用戶
                impact["affected_tenants"] = 1
                impact["affected_services"] = ["tenant_services"]
            elif intent.level == "user":
                impact["affected_users"] = 1
                impact["affected_tenants"] = 1
                impact["affected_services"] = ["user_services"]

            # 分析配置變更內容
            if intent.config_data:
                impact["configuration_changes"] = {
                    "added": [
                        k
                        for k in intent.config_data.keys()
                        if not current_config or k not in (current_config.config_data or {})
                    ],
                    "modified": [
                        k
                        for k in intent.config_data.keys()
                        if current_config and k in (current_config.config_data or {})
                    ],
                    "removed": [
                        k
                        for k in (current_config.config_data or {}).keys()
                        if k not in intent.config_data
                    ],
                }

            # 評估是否需要重啟服務
            if intent.config_data:
                critical_fields = ["allowed_providers", "default_model", "rate_limit"]
                if any(field in intent.config_data for field in critical_fields):
                    impact["estimated_downtime"] = "minimal"  # 可能需要熱重載

        except Exception as e:
            self._logger.error(f"Failed to analyze impact: {e}", exc_info=True)
            impact["error"] = str(e)

        return impact

    async def _calculate_cost_change(
        self, intent: ConfigIntent, current_config: Optional[ConfigModel]
    ) -> Optional[Dict[str, Any]]:
        """
        計算成本變化

        Args:
            intent: 配置操作意圖
            current_config: 當前配置

        Returns:
            成本變化分析（如果可計算）
        """
        try:
            # 基礎實現：簡單的成本變化估算
            # 實際應該根據模型使用量、API 調用次數等計算

            cost_change = {
                "estimated_monthly_change": 0.0,
                "change_percentage": 0.0,
                "factors": [],
            }

            if not intent.config_data:
                return cost_change

            current_data = current_config.config_data if current_config else {}
            new_data = intent.config_data

            # 檢查 rate_limit 變化（可能影響 API 調用成本）
            if "rate_limit" in new_data:
                old_limit_val = current_data.get("rate_limit", 0)
                new_limit_val = new_data.get("rate_limit", 0)
                old_limit = int(old_limit_val) if isinstance(old_limit_val, (int, float)) else 0
                new_limit = int(new_limit_val) if isinstance(new_limit_val, (int, float)) else 0
                if new_limit > old_limit:
                    cost_change["factors"].append("Increased rate limit may increase API usage")
                    cost_change["estimated_monthly_change"] += (
                        new_limit - old_limit
                    ) * 0.01  # 簡單估算
                elif new_limit < old_limit:
                    cost_change["factors"].append("Decreased rate limit may reduce API usage")
                    cost_change["estimated_monthly_change"] -= float((old_limit - new_limit) * 0.01)

            # 檢查 default_model 變化（不同模型可能有不同定價）
            if "default_model" in new_data:
                old_model = current_data.get("default_model")
                new_model = new_data.get("default_model")
                if old_model != new_model:
                    cost_change["factors"].append(f"Model change: {old_model} → {new_model}")
                    # 實際應該查詢模型定價表

            # 計算變化百分比
            if current_config and cost_change["estimated_monthly_change"] != 0:
                cost_change["change_percentage"] = float(
                    (cost_change["estimated_monthly_change"] / 100.0) * 100
                )

            return cost_change if cost_change["factors"] else None

        except Exception as e:
            self._logger.error(f"Failed to calculate cost change: {e}", exc_info=True)
            return None

    async def _assess_risk(
        self, intent: ConfigIntent, current_config: Optional[ConfigModel]
    ) -> str:
        """
        評估風險級別

        Args:
            intent: 配置操作意圖
            current_config: 當前配置

        Returns:
            風險級別（low/medium/high）
        """
        risk_score = 0

        try:
            # 1. 系統級配置變更風險較高
            if intent.level == "system":
                risk_score += 3
            elif intent.level == "tenant":
                risk_score += 2
            elif intent.level == "user":
                risk_score += 1

            # 2. 刪除操作風險較高
            if intent.action == "delete":
                risk_score += 3

            # 3. 關鍵配置項變更風險較高
            if intent.config_data:
                critical_fields = ["allowed_providers", "default_model", "rate_limit"]
                if any(field in intent.config_data for field in critical_fields):
                    risk_score += 2

            # 4. 檢查是否會影響其他租戶/用戶（收斂規則違反）
            if intent.level == "tenant" and current_config and intent.config_data:
                # 這裡可以調用合規檢查來評估風險
                # 簡化實現：如果涉及 allowed_providers 或 allowed_models，風險較高
                config_data = intent.config_data if isinstance(intent.config_data, dict) else {}
                if "allowed_providers" in config_data or "allowed_models" in config_data:
                    risk_score += 1

            # 根據風險分數確定級別
            if risk_score >= 5:
                return "high"
            elif risk_score >= 3:
                return "medium"
            else:
                return "low"

        except Exception as e:
            self._logger.error(f"Failed to assess risk: {e}", exc_info=True)
            # 評估失敗時返回高風險
            return "high"
