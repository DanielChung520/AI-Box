# 代碼功能說明: Prometheus 指標中間件（WBS-2.4: 監控與日誌）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18

"""Prometheus 指標收集中間件

用於收集 FastAPI 應用程式的性能指標，包括：
- HTTP 請求和響應時間
- 請求計數
- 錯誤率
"""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# 定義 Prometheus 指標
http_requests_total = Counter(
    "http_requests_total",
    "HTTP 請求總數",
    ["method", "endpoint", "status_code"],
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 請求處理時間（秒）",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_request_in_progress = Gauge(
    "http_requests_in_progress",
    "正在處理中的 HTTP 請求數",
    ["method", "endpoint"],
)

# 業務指標
file_uploads_total = Counter(
    "file_uploads_total",
    "文件上傳總數",
    ["status"],
)

file_upload_size_bytes = Histogram(
    "file_upload_size_bytes",
    "文件上傳大小（字節）",
    buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600],
)

active_connections = Gauge(
    "active_connections",
    "當前活躍連接數",
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Prometheus 指標收集中間件"""

    def __init__(self, app: ASGIApp, app_name: str = "ai-box-api"):
        """
        初始化 Prometheus 中間件

        Args:
            app: ASGI 應用程式
            app_name: 應用程式名稱
        """
        super().__init__(app)
        self.app_name = app_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        處理請求並收集指標

        Args:
            request: HTTP 請求
            call_next: 下一個中間件或路由處理器

        Returns:
            HTTP 響應
        """
        # 獲取端點路徑（去除查詢參數）
        endpoint = request.url.path
        method = request.method

        # 過濾指標端點（避免無限遞歸）
        if endpoint.startswith("/metrics") or endpoint.startswith("/health"):
            return await call_next(request)

        # 增加正在處理的請求數
        http_request_in_progress.labels(method=method, endpoint=endpoint).inc()
        active_connections.inc()

        # 記錄開始時間
        start_time = time.time()

        try:
            # 處理請求
            response = await call_next(request)

            # 計算處理時間
            duration = time.time() - start_time

            # 記錄指標
            status_code = response.status_code
            http_requests_total.labels(
                method=method, endpoint=endpoint, status_code=status_code
            ).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)

            return response

        except Exception:
            # 記錄錯誤
            duration = time.time() - start_time
            http_requests_total.labels(method=method, endpoint=endpoint, status_code=500).inc()
            http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
            raise

        finally:
            # 減少正在處理的請求數
            http_request_in_progress.labels(method=method, endpoint=endpoint).dec()
            active_connections.dec()


def register_file_upload_metrics(file_size: int, status: str = "success") -> None:
    """
    記錄文件上傳指標

    Args:
        file_size: 文件大小（字節）
        status: 上傳狀態（success, failed）
    """
    file_uploads_total.labels(status=status).inc()
    if status == "success":
        file_upload_size_bytes.observe(file_size)
