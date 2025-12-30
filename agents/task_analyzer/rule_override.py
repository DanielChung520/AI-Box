# 代碼功能說明: 規則覆蓋模組
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""規則覆蓋模組 - 硬性規則覆蓋 Router LLM 決策"""

import logging
from typing import Any, Dict

from agents.task_analyzer.models import RouterDecision

logger = logging.getLogger(__name__)

# 危險關鍵詞（觸發高風險）
DANGEROUS_KEYWORDS = ["delete", "execute", "deploy", "drop", "shutdown", "remove", "destroy"]

# 成本敏感關鍵詞
COST_SENSITIVE_KEYWORDS = ["便宜", "低成本", "免費", "cheap", "low cost", "free"]

# 低延遲關鍵詞
LOW_LATENCY_KEYWORDS = ["快速", "立即", "實時", "fast", "immediate", "realtime", "real-time"]


class RuleOverride:
    """規則覆蓋類 - 硬性規則覆蓋 LLM 決策"""

    def __init__(self):
        """初始化規則覆蓋"""
        self.dangerous_keywords = DANGEROUS_KEYWORDS
        self.cost_sensitive_keywords = COST_SENSITIVE_KEYWORDS
        self.low_latency_keywords = LOW_LATENCY_KEYWORDS

    def apply(self, decision: RouterDecision, query: str) -> RouterDecision:
        """
        應用規則覆蓋

        Args:
            decision: Router 決策
            query: 用戶查詢

        Returns:
            應用規則後的決策（可能被修改）
        """
        query_lower = query.lower()

        # 規則 1: 危險關鍵詞 → 高風險
        if any(keyword in query_lower for keyword in self.dangerous_keywords):
            if decision.risk_level != "high":
                logger.info(
                    "Rule override: dangerous keywords detected, setting risk_level to high"
                )
                decision.risk_level = "high"
                # 危險操作通常需要 Agent 審核
                if not decision.needs_agent:
                    decision.needs_agent = True

        # 規則 2: 成本敏感 → 強制低成本模型（通過 system_constraints）
        if any(keyword in query_lower for keyword in self.cost_sensitive_keywords):
            logger.info("Rule override: cost sensitive query detected")
            # 注意：這個規則主要影響後續的模型選擇，這裡只記錄

        # 規則 3: 低延遲要求 → 強制本地模型（通過 system_constraints）
        if any(keyword in query_lower for keyword in self.low_latency_keywords):
            logger.info("Rule override: low latency requirement detected")
            # 注意：這個規則主要影響後續的模型選擇，這裡只記錄

        return decision

    def check_risk_level(self, query: str) -> str:
        """
        檢查風險等級（獨立方法）

        Args:
            query: 用戶查詢

        Returns:
            風險等級（low/mid/high）
        """
        query_lower = query.lower()

        # 檢查危險關鍵詞
        if any(keyword in query_lower for keyword in self.dangerous_keywords):
            return "high"

        # 檢查中等風險關鍵詞（財務、法律等）
        medium_risk_keywords = ["finance", "financial", "legal", "law", "財務", "法律", "合約"]
        if any(keyword in query_lower for keyword in medium_risk_keywords):
            return "mid"

        return "low"

    def get_system_constraints(self, query: str) -> Dict[str, Any]:
        """
        根據查詢生成系統約束

        Args:
            query: 用戶查詢

        Returns:
            系統約束字典
        """
        query_lower = query.lower()
        constraints: Dict[str, Any] = {
            "max_cost": "medium",
            "allow_agents": True,
            "allow_tools": True,
        }

        # 成本敏感 → 低成本
        if any(keyword in query_lower for keyword in self.cost_sensitive_keywords):
            constraints["max_cost"] = "low"

        # 低延遲要求 → 本地模型優先
        if any(keyword in query_lower for keyword in self.low_latency_keywords):
            constraints["prefer_local"] = True
            constraints["max_latency_ms"] = 1000

        return constraints
