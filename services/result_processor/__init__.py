# 代碼功能說明: Result Processor 服務適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""Result Processor 服務適配器 - 重新導出 agents.services.processing 的模組"""

# 從 agents.services 模組重新導出
from agents.services.processing.aggregator import ResultAggregator  # noqa: F401
from agents.services.processing.report_generator import ReportGenerator  # noqa: F401

__all__ = ["ResultAggregator", "ReportGenerator"]
