# 代碼功能說明: MCP Protocol 數據模型
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""MCP Protocol 消息和請求/響應模型"""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class MCPMessage(BaseModel):
    """MCP 消息基類"""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC 版本")
    id: Optional[Union[str, int]] = Field(default=None, description="消息 ID")


class MCPRequest(MCPMessage):
    """MCP 請求消息"""

    method: str = Field(..., description="方法名稱")
    params: Optional[Dict[str, Any]] = Field(default=None, description="請求參數")


class MCPResponse(MCPMessage):
    """MCP 響應消息"""

    result: Optional[Dict[str, Any]] = Field(default=None, description="響應結果")


class MCPError(BaseModel):
    """MCP 錯誤信息"""

    code: int = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤消息")
    data: Optional[Dict[str, Any]] = Field(default=None, description="錯誤詳情")


class MCPErrorResponse(MCPMessage):
    """MCP 錯誤響應"""

    error: MCPError = Field(..., description="錯誤信息")


class MCPInitializeRequest(MCPRequest):
    """初始化請求"""

    method: str = Field(default="initialize", description="方法名稱")
    params: Dict[str, Any] = Field(
        ...,
        description="初始化參數",
    )


class MCPInitializeResponse(MCPResponse):
    """初始化響應"""

    result: Dict[str, Any] = Field(
        ...,
        description="初始化結果",
    )


class MCPTool(BaseModel):
    """MCP 工具定義"""

    name: str = Field(..., description="工具名稱")
    description: str = Field(..., description="工具描述")
    inputSchema: Dict[str, Any] = Field(..., description="輸入 Schema")


class MCPToolCallRequest(MCPRequest):
    """工具調用請求"""

    method: str = Field(default="tools/call", description="方法名稱")
    params: Dict[str, Any] = Field(..., description="工具調用參數")


class MCPToolCallResponse(MCPResponse):
    """工具調用響應"""

    result: Dict[str, Any] = Field(
        ...,
        description="工具調用結果",
    )


class MCPListToolsRequest(MCPRequest):
    """列出工具請求"""

    method: str = Field(default="tools/list", description="方法名稱")


class MCPListToolsResponse(MCPResponse):
    """列出工具響應"""

    result: Dict[str, Any] = Field(
        ...,
        description="工具列表",
    )
