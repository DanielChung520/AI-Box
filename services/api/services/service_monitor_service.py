# 代碼功能說明: 服務狀態監控服務
# 創建日期: 2026-01-17 17:13 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-17 17:13 UTC+8

"""Service Monitor Service

提供統一的服務狀態監控服務，支持多個服務的健康檢查。
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx
import psutil
import structlog

from database.arangodb import ArangoDBClient
from database.redis import get_redis_client
from services.api.models.service_status import ServiceHealthCheck

logger = structlog.get_logger(__name__)

# 服務配置（端口、端點等）
SERVICE_CONFIGS: Dict[str, Dict[str, Any]] = {
    "fastapi": {
        "type": "api",
        "port": 8000,
        "health_endpoint": "http://localhost:8000/api/health",
    },
    "arangodb": {
        "type": "database",
        "port": 8529,
        "health_endpoint": None,  # 使用數據庫連接檢查
    },
    "redis": {
        "type": "cache",
        "port": 6379,
        "health_endpoint": None,  # 使用連接檢查
    },
    # ChromaDB 已移除（已迁移到 Qdrant）
    "rq_worker": {
        "type": "worker",
        "port": None,
        "health_endpoint": None,  # 使用進程檢查
    },
    "rq_dashboard": {
        "type": "dashboard",
        "port": 9181,
        "health_endpoint": "http://localhost:9181",
    },
    "seaweedfs": {
        "type": "storage",
        "port": 9333,  # Master 端口
        "health_endpoint": "http://localhost:9333/status",
        "filer_endpoint": "http://localhost:8888",
        "s3_endpoint": "http://localhost:8333",
    },
    "mcp_server": {
        "type": "api",
        "port": 8002,
        "health_endpoint": "http://localhost:8002/health",
    },
    "frontend": {
        "type": "frontend",
        "port": 3000,
        "health_endpoint": "http://localhost:3000",
    },
}


class ServiceMonitorService:
    """服務狀態監控服務"""

    def __init__(self):
        """初始化服務監控服務"""
        self._logger = logger
        self._http_client = httpx.AsyncClient(timeout=5.0)

    async def check_service(self, service_name: str) -> ServiceHealthCheck:
        """
        檢查單個服務狀態

        Args:
            service_name: 服務名稱

        Returns:
            服務健康檢查結果
        """
        start_time = time.time()

        try:
            if service_name == "fastapi":
                result = await self.check_fastapi()
            elif service_name == "arangodb":
                result = await self.check_arangodb()
            elif service_name == "redis":
                result = await self.check_redis()
            # ChromaDB 监控已移除（已迁移到 Qdrant）
            elif service_name == "rq_worker":
                result = await self.check_rq_worker()
            elif service_name == "rq_dashboard":
                result = await self.check_rq_dashboard()
            elif service_name == "seaweedfs":
                result = await self.check_seaweedfs()
            elif service_name == "mcp_server":
                result = await self.check_mcp_server()
            elif service_name == "frontend":
                result = await self.check_frontend()
            else:
                result = ServiceHealthCheck(
                    service_name=service_name,
                    status="unknown",
                    health_status="unhealthy",
                    error_message=f"Unknown service: {service_name}",
                )

            # 計算響應時間
            response_time = (time.time() - start_time) * 1000  # 轉換為毫秒
            result.response_time_ms = response_time

            return result

        except Exception as e:
            self._logger.error(
                f"Failed to check service: service_name={service_name}, error={str(e)}",
                exc_info=True,
            )
            return ServiceHealthCheck(
                service_name=service_name,
                status="error",
                health_status="unhealthy",
                error_message=str(e),
                response_time_ms=(time.time() - start_time) * 1000,
            )

    async def check_all_services(self) -> List[ServiceHealthCheck]:
        """
        檢查所有服務狀態

        Returns:
            所有服務的健康檢查結果列表
        """
        service_names = list(SERVICE_CONFIGS.keys())
        results = []

        for service_name in service_names:
            result = await self.check_service(service_name)
            results.append(result)

        return results

    async def check_fastapi(self) -> ServiceHealthCheck:
        """檢查 FastAPI 服務"""
        try:
            response = await self._http_client.get("http://localhost:8000/api/health")
            if response.status_code == 200:
                return ServiceHealthCheck(
                    service_name="fastapi",
                    status="running",
                    health_status="healthy",
                    metadata={"status_code": response.status_code},
                )
            else:
                return ServiceHealthCheck(
                    service_name="fastapi",
                    status="error",
                    health_status="unhealthy",
                    error_message=f"HTTP {response.status_code}",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="fastapi",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_arangodb(self) -> ServiceHealthCheck:
        """檢查 ArangoDB 服務"""
        try:
            client = ArangoDBClient(connect_on_init=False)
            client._connect()  # 手動連接

            if client.db is None:
                return ServiceHealthCheck(
                    service_name="arangodb",
                    status="error",
                    health_status="unhealthy",
                    error_message="Database connection failed",
                )

            # 執行簡單查詢測試連接
            try:
                # 嘗試獲取數據庫信息
                db_info = client.db.properties()
                return ServiceHealthCheck(
                    service_name="arangodb",
                    status="running",
                    health_status="healthy",
                    metadata={"database": db_info.get("name", "unknown")},
                )
            except Exception as e:
                return ServiceHealthCheck(
                    service_name="arangodb",
                    status="error",
                    health_status="unhealthy",
                    error_message=str(e),
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="arangodb",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_redis(self) -> ServiceHealthCheck:
        """檢查 Redis 服務"""
        try:
            redis_client = get_redis_client()
            result = redis_client.ping()

            if result:
                # 獲取 Redis 信息
                info = redis_client.info()
                return ServiceHealthCheck(
                    service_name="redis",
                    status="running",
                    health_status="healthy",
                    metadata={
                        "version": info.get("redis_version", "unknown"),
                        "used_memory": info.get("used_memory_human", "unknown"),
                    },
                )
            else:
                return ServiceHealthCheck(
                    service_name="redis",
                    status="error",
                    health_status="unhealthy",
                    error_message="PING failed",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="redis",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    # check_chromadb 方法已移除（已迁移到 Qdrant）

    async def check_rq_worker(self) -> ServiceHealthCheck:
        """檢查 RQ Worker 服務"""
        try:
            # 檢查 RQ Worker 進程
            # 查找包含 "rq worker" 的進程
            worker_processes = []
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    cmdline = proc.info.get("cmdline", [])
                    if cmdline and any(
                        "rq" in str(arg).lower() and "worker" in str(arg).lower() for arg in cmdline
                    ):
                        worker_processes.append(proc.info["pid"])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if worker_processes:
                return ServiceHealthCheck(
                    service_name="rq_worker",
                    status="running",
                    health_status="healthy",
                    metadata={"pids": worker_processes, "worker_count": len(worker_processes)},
                )
            else:
                return ServiceHealthCheck(
                    service_name="rq_worker",
                    status="stopped",
                    health_status="unhealthy",
                    error_message="No RQ worker processes found",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="rq_worker",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_rq_dashboard(self) -> ServiceHealthCheck:
        """檢查 RQ Dashboard 服務"""
        try:
            response = await self._http_client.get("http://localhost:9181", follow_redirects=True)
            if response.status_code in [200, 302]:  # 302 是重定向，也是正常的
                return ServiceHealthCheck(
                    service_name="rq_dashboard",
                    status="running",
                    health_status="healthy",
                    metadata={"status_code": response.status_code},
                )
            else:
                return ServiceHealthCheck(
                    service_name="rq_dashboard",
                    status="error",
                    health_status="unhealthy",
                    error_message=f"HTTP {response.status_code}",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="rq_dashboard",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_seaweedfs(self) -> ServiceHealthCheck:
        """檢查 SeaweedFS 服務"""
        try:
            # 檢查 Master
            master_response = await self._http_client.get("http://localhost:9333/status")
            master_healthy = master_response.status_code == 200

            # 檢查 Filer
            filer_healthy = False
            try:
                filer_response = await self._http_client.get("http://localhost:8888")
                filer_healthy = filer_response.status_code in [200, 404]  # 404 也可能表示服務運行中
            except Exception:
                pass

            # 檢查 S3 API（可選）
            s3_healthy = False
            try:
                s3_response = await self._http_client.get("http://localhost:8333", timeout=2.0)
                s3_healthy = s3_response.status_code in [
                    200,
                    403,
                    404,
                ]  # 403/404 也可能表示服務運行中
            except Exception:
                pass

            if master_healthy:
                health_status = "healthy" if (filer_healthy or s3_healthy) else "degraded"
                return ServiceHealthCheck(
                    service_name="seaweedfs",
                    status="running",
                    health_status=health_status,
                    metadata={
                        "master": "healthy",
                        "filer": "healthy" if filer_healthy else "unavailable",
                        "s3": "healthy" if s3_healthy else "unavailable",
                    },
                )
            else:
                return ServiceHealthCheck(
                    service_name="seaweedfs",
                    status="error",
                    health_status="unhealthy",
                    error_message="Master service unavailable",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="seaweedfs",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_mcp_server(self) -> ServiceHealthCheck:
        """檢查 MCP Server 服務"""
        try:
            # 嘗試多個可能的健康檢查端點
            endpoints = [
                "http://localhost:8002/health",
                "http://localhost:8002/api/health",
                "http://localhost:8002",
            ]

            for endpoint in endpoints:
                try:
                    response = await self._http_client.get(endpoint, timeout=2.0)
                    if response.status_code in [200, 404]:  # 404 也可能表示服務運行中
                        return ServiceHealthCheck(
                            service_name="mcp_server",
                            status="running",
                            health_status="healthy",
                            metadata={"endpoint": endpoint, "status_code": response.status_code},
                        )
                except Exception:
                    continue

            # 如果所有端點都失敗，檢查端口是否開放
            return ServiceHealthCheck(
                service_name="mcp_server",
                status="unknown",
                health_status="unhealthy",
                error_message="No health endpoint responded",
            )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="mcp_server",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def check_frontend(self) -> ServiceHealthCheck:
        """檢查 Frontend 服務"""
        try:
            response = await self._http_client.get("http://localhost:3000", timeout=3.0)
            if response.status_code in [200, 302, 404]:  # 這些狀態碼都表示服務運行中
                return ServiceHealthCheck(
                    service_name="frontend",
                    status="running",
                    health_status="healthy",
                    metadata={"status_code": response.status_code},
                )
            else:
                return ServiceHealthCheck(
                    service_name="frontend",
                    status="error",
                    health_status="unhealthy",
                    error_message=f"HTTP {response.status_code}",
                )
        except Exception as e:
            return ServiceHealthCheck(
                service_name="frontend",
                status="error",
                health_status="unhealthy",
                error_message=str(e),
            )

    async def close(self) -> None:
        """關閉 HTTP 客戶端"""
        await self._http_client.aclose()


def get_service_monitor_service() -> ServiceMonitorService:
    """
    獲取 ServiceMonitorService 實例（單例模式）

    Returns:
        ServiceMonitorService 實例
    """
    global _service
    if _service is None:
        _service = ServiceMonitorService()
    return _service


_service: Optional[ServiceMonitorService] = None
