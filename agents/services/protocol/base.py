# 代碼功能說明: Agent Service Protocol 基礎接口定義
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Agent Service Protocol 基礎接口定義

定義 Agent 服務的標準接口，支持多種通信方式（HTTP、MCP）。
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AgentServiceProtocolType(str, Enum):
    """Agent Service 協議類型"""

    HTTP = "http"
    MCP = "mcp"


class AgentServiceStatus(str, Enum):
    """Agent 服務狀態"""

    AVAILABLE = "available"
    BUSY = "busy"
    UNAVAILABLE = "unavailable"
    ERROR = "error"


class AgentServiceRequest(BaseModel):
    """Agent 服務請求模型"""

    task_id: str = Field(..., description="任務 ID")
    task_type: str = Field(..., description="任務類型")
    task_data: Dict[str, Any] = Field(..., description="任務數據")
    context: Optional[Dict[str, Any]] = Field(None, description="上下文信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class AgentServiceResponse(BaseModel):
    """Agent 服務響應模型"""

    task_id: str = Field(..., description="任務 ID")
    status: str = Field(..., description="執行狀態")
    result: Optional[Dict[str, Any]] = Field(None, description="執行結果")
    error: Optional[str] = Field(None, description="錯誤信息")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元數據")


class AgentServiceProtocol(ABC):
    """Agent 服務協議抽象基類

    定義 Agent 服務的標準接口，所有 Agent 服務實現都應該遵循此協議。
    """

    @abstractmethod
    async def execute(self, request: AgentServiceRequest) -> AgentServiceResponse:
        """
        執行任務

        Args:
            request: Agent 服務請求

        Returns:
            Agent 服務響應
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> AgentServiceStatus:
        """
        健康檢查

        Returns:
            服務狀態
        """
        raise NotImplementedError

    @abstractmethod
    async def get_capabilities(self) -> Dict[str, Any]:
        """
        獲取服務能力

        Returns:
            服務能力描述
        """
        raise NotImplementedError
