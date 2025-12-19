# 代碼功能說明: MCP Client 連線管理器
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Client 連線管理器模組"""

import logging
from typing import Any, Dict, List

from mcp_client.connection.pool import ConnectionPool, LoadBalanceStrategy

logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """MCP Client 連線管理器"""

    def __init__(
        self,
        endpoints: List[str],
        load_balance_strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        health_check_interval: int = 30,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        初始化連線管理器

        Args:
            endpoints: 端點 URL 列表
            load_balance_strategy: 負載均衡策略
            health_check_interval: 健康檢查間隔（秒）
            max_retries: 最大重試次數
            retry_delay: 重試延遲（秒）
        """
        self.pool = ConnectionPool(
            endpoints=endpoints,
            load_balance_strategy=load_balance_strategy,
            health_check_interval=health_check_interval,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        self.request_id_counter = 0

    async def initialize(self) -> None:
        """初始化連線管理器"""
        await self.pool.initialize()

    def generate_request_id(self) -> int:
        """
        生成請求 ID

        Returns:
            int: 請求 ID
        """
        self.request_id_counter += 1
        return self.request_id_counter

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        調用工具（帶重試和負載均衡）

        Args:
            name: 工具名稱
            arguments: 工具參數

        Returns:
            Dict[str, Any]: 工具執行結果
        """
        return await self.pool.call_with_retry(
            lambda client, *args, **kwargs: client.call_tool(*args, **kwargs),
            name,
            arguments,
        )

    async def list_tools(self) -> List:
        """
        列出可用工具

        Returns:
            List: 工具列表
        """
        conn = self.pool.get_connection()
        if conn is None:
            raise Exception("No healthy connections available")
        return await conn.client.list_tools()

    async def refresh_tools(self) -> List:
        """
        刷新工具列表

        Returns:
            List: 工具列表
        """
        conn = self.pool.get_connection()
        if conn is None:
            raise Exception("No healthy connections available")
        return await conn.client.refresh_tools()

    def get_stats(self) -> Dict:
        """
        獲取連線管理器統計信息

        Returns:
            Dict: 統計信息
        """
        return self.pool.get_stats()

    async def close(self) -> None:
        """關閉連線管理器"""
        await self.pool.close()
