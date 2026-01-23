# 代碼功能說明: Prometheus 指標中間件（WBS-2.4: 監控與日誌）
# 創建日期: 2025-12-18
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 13:35 UTC+8

"""Prometheus 指標收集中間件

用於收集 FastAPI 應用程式的性能指標，包括：
- HTTP 請求和響應時間
- 請求計數
- 錯誤率
- 系統資源使用情況（CPU、內存、磁盤）
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Optional

import psutil
from fastapi import Request, Response
from prometheus_client import Counter, Gauge, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)

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
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
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

# 系統資源指標
cpu_usage_percent = Gauge(
    "cpu_usage_percent",
    "CPU 使用率（百分比）",
)

memory_usage_percent = Gauge(
    "memory_usage_percent",
    "內存使用率（百分比）",
)

memory_usage_bytes = Gauge(
    "memory_usage_bytes",
    "內存使用量（字節）",
)

disk_usage_percent = Gauge(
    "disk_usage_percent",
    "磁盤使用率（百分比）",
    ["path"],
)

disk_usage_bytes = Gauge(
    "disk_usage_bytes",
    "磁盤使用量（字節）",
    ["path"],
)

# ============================================================================
# MoE (Mixture of Experts) Metrics
# ============================================================================

moe_model_selections_total = Counter(
    "moe_model_selections_total",
    "MoE 模型選擇總次數",
    ["scene", "model", "status"],
)

moe_selection_duration_seconds = Histogram(
    "moe_selection_duration_seconds",
    "MoE 模型選擇耗時（秒）",
    ["scene"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

moe_active_scenes = Gauge(
    "moe_active_scenes",
    "活躍的 MoE 場景數量",
)

moe_fallback_count_total = Counter(
    "moe_fallback_count_total",
    "MoE 回退總次數",
    ["scene", "original_model", "fallback_model"],
)

moe_user_preferences_total = Counter(
    "moe_user_preferences_total",
    "MoE 用戶偏好設置總次數",
    ["scene", "user_id"],
)

moe_provider_health_status = Gauge(
    "moe_provider_health_status",
    "MoE 提供商健康狀態",
    ["provider", "status"],
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


async def update_system_metrics() -> None:
    """
    定期更新系統資源指標

    每 15 秒更新一次 CPU、內存和磁盤使用情況
    """
    while True:
        try:
            # 更新 CPU 使用率（間隔 1 秒採樣）
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_usage_percent.set(cpu_percent)

            # 更新內存使用率
            memory = psutil.virtual_memory()
            memory_usage_percent.set(memory.percent)
            memory_usage_bytes.set(memory.used)

            # 更新磁盤使用率（根目錄）
            disk = psutil.disk_usage("/")
            disk_usage_percent.labels(path="/").set(disk.percent)
            disk_usage_bytes.labels(path="/").set(disk.used)

            logger.debug(
                f"System metrics updated: CPU={cpu_percent:.1f}%, "
                f"Memory={memory.percent:.1f}%, Disk={disk.percent:.1f}%"
            )

        except Exception as e:
            logger.error(f"Failed to update system metrics: {e}")

        # 每 15 秒更新一次
        await asyncio.sleep(15)


def start_system_metrics_task() -> None:
    """
    啟動系統資源指標收集後台任務
    """
    try:
        asyncio.create_task(update_system_metrics())
        logger.info("System metrics background task started")
    except Exception as e:
        logger.error(f"Failed to start system metrics task: {e}")


# ============================================================================
# MoE Metrics 記錄函數
# ============================================================================


def record_moe_model_selection(
    scene: str,
    model: str,
    status: str,
    duration: float,
    fallback_model: Optional[str] = None,
) -> None:
    """
    記錄 MoE 模型選擇指標

    Args:
        scene: 場景名稱
        model: 選擇的模型
        status: 狀態 (success, fallback, error)
        duration: 選擇耗時（秒）
        fallback_model: 回退模型（如果發生了回退）
    """
    moe_model_selections_total.labels(scene=scene, model=model, status=status).inc()
    moe_selection_duration_seconds.labels(scene=scene).observe(duration)

    if status == "fallback" and fallback_model:
        moe_fallback_count_total.labels(
            scene=scene, original_model=model, fallback_model=fallback_model
        ).inc()


def record_moe_user_preference(scene: str, user_id: str) -> None:
    """
    記錄 MoE 用戶偏好設置

    Args:
        scene: 場景名稱
        user_id: 用戶 ID
    """
    moe_user_preferences_total.labels(scene=scene, user_id=user_id).inc()


def update_moe_active_scenes(count: int) -> None:
    """
    更新活躍 MoE 場景數量

    Args:
        count: 活躍場景數量
    """
    moe_active_scenes.set(count)


def update_moe_provider_health(provider: str, healthy: bool) -> None:
    """
    更新 MoE 提供商健康狀態

    Args:
        provider: 提供商名稱
        healthy: 是否健康
    """
    moe_provider_health_status.labels(
        provider=provider, status="healthy" if healthy else "unhealthy"
    ).set(1 if healthy else 0)
