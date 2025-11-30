# 代碼功能說明: 監控中間件
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""監控中間件模組"""

import time
import logging
from .metrics import Metrics

logger = logging.getLogger(__name__)


def create_monitoring_middleware(metrics: Metrics):
    """
    創建監控中間件

    Args:
        metrics: 指標收集器實例

    Returns:
        Callable: 中間件函數
    """

    async def monitoring_middleware(request, call_next):
        """監控中間件實現"""
        start_time = time.time()
        method = request.url.path

        try:
            response = await call_next(request)
            is_error = response.status_code >= 400
            latency = time.time() - start_time
            metrics.record_request(method, latency, is_error)
            return response
        except Exception as e:
            latency = time.time() - start_time
            metrics.record_request(method, latency, is_error=True)
            logger.error(f"Request error: {e}")
            raise

    return monitoring_middleware
