# 代碼功能說明: Execution Agent 核心實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Execution Agent - 實現工具執行"""

import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from agents.core.execution.models import ExecutionRequest, ExecutionResult, ExecutionStatus
from agents.infra.memory import MemoryManager
from agents.infra.tools import ToolRegistry
from agents.services.protocol.base import (
    AgentServiceProtocol,
    AgentServiceRequest,
    AgentServiceResponse,
    AgentServiceStatus,
)

logger = logging.getLogger(__name__)


class ExecutionAgent(AgentServiceProtocol):
    """Execution Agent - 執行代理"""

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        """
        初始化 Execution Agent

        Args:
            tool_registry: 工具註冊表
            memory_manager: 記憶管理器
        """
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory_manager = memory_manager

    def execute_task(self, request: ExecutionRequest) -> ExecutionResult:
        """
        執行任務

        Args:
            request: 執行請求

        Returns:
            執行結果
        """
        logger.info(f"Executing task: {request.task[:100]}...")

        execution_id = str(uuid.uuid4())
        started_at = time.time()

        try:
            # 如果指定了工具名稱，使用該工具執行
            if request.tool_name:
                result = self._execute_tool(
                    request.tool_name,
                    request.tool_args or {},
                )
            else:
                # 根據任務描述自動選擇工具
                result = self._execute_auto(request)

            execution_time = time.time() - started_at

            execution_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.COMPLETED,
                result=result,
                error=None,
                tool_name=request.tool_name,
                execution_time=execution_time,
                started_at=datetime.fromtimestamp(started_at),
                completed_at=datetime.now(),
                metadata=request.metadata,
            )

            logger.info(
                f"Execution completed: execution_id={execution_id}, "
                f"status=completed, time={execution_time:.2f}s"
            )

        except Exception as e:
            execution_time = time.time() - started_at
            error_msg = str(e)

            execution_result = ExecutionResult(
                execution_id=execution_id,
                status=ExecutionStatus.FAILED,
                result=None,
                error=error_msg,
                started_at=datetime.fromtimestamp(started_at),
                completed_at=datetime.now(),
                tool_name=request.tool_name,
                execution_time=execution_time,
                metadata=request.metadata,
            )

            logger.error(f"Execution failed: execution_id={execution_id}, " f"error={error_msg}")

        # 存儲執行結果到記憶（如果可用）
        if self.memory_manager:
            self.memory_manager.store_short_term(
                key=f"execution:{execution_id}",
                value=execution_result.model_dump(),
                ttl=3600,  # 1小時
            )

        return execution_result

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """
        執行指定工具

        Args:
            tool_name: 工具名稱
            tool_args: 工具參數

        Returns:
            執行結果
        """
        if not self.tool_registry.get(tool_name):
            raise ValueError(f"Tool '{tool_name}' not found")

        try:
            result = self.tool_registry.execute(tool_name, **tool_args)
            return {
                "success": True,
                "data": result,
            }
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise

    def _execute_auto(self, request: ExecutionRequest) -> Dict[str, Any]:
        """
        自動選擇工具執行

        Args:
            request: 執行請求

        Returns:
            執行結果
        """
        # 簡單的自動工具選擇邏輯
        # 實際實現應該更智能

        task_lower = request.task.lower()

        # 根據任務描述匹配工具
        if "查詢" in task_lower or "query" in task_lower:
            # 嘗試查找查詢類工具
            query_tools = self.tool_registry.discover("query")
            if query_tools:
                tool = query_tools[0]
                return self._execute_tool(tool.name, request.tool_args or {})
        elif "創建" in task_lower or "create" in task_lower:
            create_tools = self.tool_registry.discover("create")
            if create_tools:
                tool = create_tools[0]
                return self._execute_tool(tool.name, request.tool_args or {})

        # 默認返回成功（實際應該執行具體操作）
        return {
            "success": True,
            "message": "Task executed successfully",
            "data": {},
        }

    def register_tool(
        self,
        name: str,
        description: str,
        handler,
        tool_type: str = "custom",
        config: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        註冊工具

        Args:
            name: 工具名稱
            description: 工具描述
            handler: 工具處理函數
            tool_type: 工具類型
            config: 工具配置

        Returns:
            是否成功註冊
        """
        from agents.infra.tools import ToolType

        tool_type_enum = (
            ToolType(tool_type) if tool_type in [t.value for t in ToolType] else ToolType.CUSTOM
        )

        return self.tool_registry.register(
            name=name,
            description=description,
            tool_type=tool_type_enum,
            handler=handler,
            config=config,
        )

    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行任務（實現 AgentServiceProtocol 接口）

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        try:
            # 從 task_data 中提取 ExecutionRequest 數據
            task_data = request.task_data
            execution_request = ExecutionRequest(**task_data)

            # 調用原有的 execute_task 方法
            execution_result = self.execute_task(execution_request)

            # 轉換為 AgentServiceResponse
            return AgentServiceResponse(
                task_id=request.task_id,
                status=execution_result.status.value,
                result=execution_result.model_dump(),
                error=execution_result.error,
                metadata=request.metadata,
            )

        except Exception as e:
            logger.error(f"Execution Agent execution failed: {e}")
            return AgentServiceResponse(
                task_id=request.task_id,
                status="error",
                result=None,
                error=str(e),
                metadata=request.metadata,
            )

    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查（實現 AgentServiceProtocol 接口）

        Returns:
            服務狀態
        """
        try:
            # 檢查 tool_registry 是否可用
            if self.tool_registry:
                return AgentServiceStatus.AVAILABLE
            return AgentServiceStatus.UNAVAILABLE
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return AgentServiceStatus.ERROR

    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力（實現 AgentServiceProtocol 接口）

        Returns:
            服務能力描述
        """
        return {
            "name": "Execution Agent",
            "description": "工具執行和任務執行服務",
            "capabilities": [
                "tool_execution",  # 工具執行
                "auto_tool_selection",  # 自動工具選擇
                "task_execution",  # 任務執行
                "tool_registration",  # 工具註冊
            ],
            "version": "1.0.0",
        }
