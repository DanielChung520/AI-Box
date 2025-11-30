# 代碼功能說明: MCP Client 連線池實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Client 連線池實現模組"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import time

from ..client import MCPClient

logger = logging.getLogger(__name__)


class LoadBalanceStrategy(str, Enum):
    """負載均衡策略"""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"


class ConnectionStatus(str, Enum):
    """連線狀態"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ConnectionInfo:
    """連線信息"""

    def __init__(
        self,
        endpoint: str,
        client: MCPClient,
        weight: int = 1,
    ):
        """
        初始化連線信息

        Args:
            endpoint: 端點 URL
            client: MCP Client 實例
            weight: 權重（用於負載均衡）
        """
        self.endpoint = endpoint
        self.client = client
        self.weight = weight
        self.status = ConnectionStatus.UNKNOWN
        self.last_health_check: Optional[float] = None
        self.failure_count = 0
        self.success_count = 0
        self.last_error: Optional[str] = None
        self.lock = asyncio.Lock()

    async def health_check(self) -> bool:
        """
        執行健康檢查

        Returns:
            bool: 是否健康
        """
        try:
            # 嘗試初始化或刷新工具列表
            if not self.client.initialized:
                await self.client.initialize()
            else:
                await self.client.refresh_tools()

            self.status = ConnectionStatus.HEALTHY
            self.last_health_check = time.time()
            self.success_count += 1
            self.failure_count = 0
            return True
        except Exception as e:
            self.status = ConnectionStatus.UNHEALTHY
            self.last_health_check = time.time()
            self.failure_count += 1
            self.last_error = str(e)
            logger.warning(f"Health check failed for {self.endpoint}: {e}")
            return False


class ConnectionPool:
    """MCP Client 連線池"""

    def __init__(
        self,
        endpoints: List[str],
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        health_check_interval: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        初始化連線池

        Args:
            endpoints: 端點 URL 列表
            load_balance_strategy: 負載均衡策略
            health_check_interval: 健康檢查間隔（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲（秒）
        """
        self.endpoints = endpoints
        self.load_balance_strategy = load_balance_strategy
        self.health_check_interval = health_check_interval
        self.max_retries = max_retries
        self.retry_delay = retry_delay

        self.connections: Dict[str, ConnectionInfo] = {}
        self.current_index = 0  # 用於輪詢
        self.health_check_task: Optional[asyncio.Task] = None
        self._initialized = False

        # 初始化連線
        for endpoint in endpoints:
            client = MCPClient(endpoint)
            conn_info = ConnectionInfo(endpoint, client)
            self.connections[endpoint] = conn_info

    async def initialize(self) -> None:
        """初始化連線池"""
        if self._initialized:
            return

        # 初始化所有連線
        for conn_info in self.connections.values():
            try:
                await conn_info.client.initialize()
                conn_info.status = ConnectionStatus.HEALTHY
            except Exception as e:
                logger.error(
                    f"Failed to initialize connection to {conn_info.endpoint}: {e}"
                )
                conn_info.status = ConnectionStatus.UNHEALTHY

        # 啟動健康檢查任務
        self.health_check_task = asyncio.create_task(self._health_check_loop())
        self._initialized = True
        logger.info(
            f"Connection pool initialized with {len(self.connections)} connections"
        )

    async def _health_check_loop(self) -> None:
        """健康檢查循環"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _perform_health_checks(self) -> None:
        """執行所有連線的健康檢查"""
        tasks = [conn.health_check() for conn in self.connections.values()]
        await asyncio.gather(*tasks, return_exceptions=True)

    def _select_connection_round_robin(self) -> Optional[ConnectionInfo]:
        """輪詢選擇連線"""
        healthy_connections = [
            conn
            for conn in self.connections.values()
            if conn.status == ConnectionStatus.HEALTHY
        ]
        if not healthy_connections:
            return None

        conn = healthy_connections[self.current_index % len(healthy_connections)]
        self.current_index += 1
        return conn

    def _select_connection_random(self) -> Optional[ConnectionInfo]:
        """隨機選擇連線"""
        import random

        healthy_connections = [
            conn
            for conn in self.connections.values()
            if conn.status == ConnectionStatus.HEALTHY
        ]
        if not healthy_connections:
            return None
        return random.choice(healthy_connections)

    def _select_connection_least_connections(self) -> Optional[ConnectionInfo]:
        """選擇連接數最少的連線"""
        healthy_connections = [
            conn
            for conn in self.connections.values()
            if conn.status == ConnectionStatus.HEALTHY
        ]
        if not healthy_connections:
            return None
        # 簡單實現：選擇失敗次數最少的
        return min(healthy_connections, key=lambda c: c.failure_count)

    def get_connection(self) -> Optional[ConnectionInfo]:
        """
        根據負載均衡策略獲取連線

        Returns:
            ConnectionInfo: 連線信息，如果沒有可用連線則返回 None
        """
        if self.load_balance_strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_connection_round_robin()
        elif self.load_balance_strategy == LoadBalanceStrategy.RANDOM:
            return self._select_connection_random()
        elif self.load_balance_strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._select_connection_least_connections()
        else:
            return self._select_connection_round_robin()

    async def call_with_retry(self, method: Callable, *args, **kwargs) -> Any:
        """
        帶重試的調用

        Args:
            method: 要調用的方法
            *args: 位置參數
            **kwargs: 關鍵字參數

        Returns:
            Any: 調用結果
        """
        last_error = None
        for attempt in range(self.max_retries):
            conn = self.get_connection()
            if conn is None:
                raise Exception("No healthy connections available")

            try:
                return await method(conn.client, *args, **kwargs)
            except Exception as e:
                last_error = e
                conn.status = ConnectionStatus.UNHEALTHY
                conn.failure_count += 1
                conn.last_error = str(e)
                logger.warning(
                    f"Call failed on {conn.endpoint} (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))

        raise Exception(f"All retry attempts failed. Last error: {last_error}")

    def get_stats(self) -> Dict:
        """
        獲取連線池統計信息

        Returns:
            Dict: 統計信息
        """
        healthy_count = sum(
            1
            for conn in self.connections.values()
            if conn.status == ConnectionStatus.HEALTHY
        )
        return {
            "total_connections": len(self.connections),
            "healthy_connections": healthy_count,
            "unhealthy_connections": len(self.connections) - healthy_count,
            "connections": {
                endpoint: {
                    "status": conn.status.value,
                    "failure_count": conn.failure_count,
                    "success_count": conn.success_count,
                    "last_health_check": conn.last_health_check,
                    "last_error": conn.last_error,
                }
                for endpoint, conn in self.connections.items()
            },
        }

    async def close(self) -> None:
        """關閉連線池"""
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        for conn in self.connections.values():
            await conn.client.close()

        self._initialized = False
        logger.info("Connection pool closed")
