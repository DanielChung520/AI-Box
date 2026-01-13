# 代碼功能說明: Data Agent MCP Server 實現
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent MCP Server"""

# 導入 AI-Box 項目的模塊
import sys
from pathlib import Path

# 導入 Data Agent（在 datalake-system 中）
from data_agent.agent import DataAgent

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.services.protocol.base import AgentServiceRequest
from mcp.server.server import MCPServer

# 初始化 Data Agent
data_agent = DataAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="data-agent",
    version="1.0.0",
)


# 註冊工具：執行數據查詢任務
async def execute_data_agent_task_handler(arguments: dict) -> dict:
    """執行數據查詢任務工具處理器"""
    try:
        # 構建 AgentServiceRequest
        request = AgentServiceRequest(
            task_id=arguments.get("task_id", "mcp-task"),
            task_type=arguments.get("task_type", "data_query"),
            task_data=arguments.get("task_data", {}),
            context=arguments.get("context"),
            metadata=arguments.get("metadata"),
        )

        # 調用 Data Agent
        result = await data_agent.execute(request)

        # 返回結果
        if hasattr(result, "model_dump"):
            return result.model_dump()
        elif hasattr(result, "dict"):
            return result.dict()
        else:
            return result  # type: ignore[return-value]

    except Exception as e:
        return {
            "task_id": arguments.get("task_id", "mcp-task"),
            "status": "error",
            "result": None,
            "error": str(e),
            "metadata": arguments.get("metadata"),
        }


mcp_server.register_tool(
    name="execute_data_agent_task",
    description="執行數據查詢任務（Text-to-SQL、查詢執行、Datalake 查詢、數據字典管理、Schema 管理等）",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任務 ID（可選）",
            },
            "task_type": {
                "type": "string",
                "description": "任務類型（可選，默認：data_query）",
            },
            "task_data": {
                "type": "object",
                "description": "任務數據（必需），包含 action 和其他參數",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作類型（text_to_sql/execute_query/validate_query/get_schema/query_datalake/create_dictionary/get_dictionary/create_schema/validate_data）",
                        "enum": [
                            "text_to_sql",
                            "execute_query",
                            "validate_query",
                            "get_schema",
                            "query_datalake",
                            "create_dictionary",
                            "get_dictionary",
                            "create_schema",
                            "validate_data",
                        ],
                    },
                },
                "required": ["action"],
            },
            "context": {
                "type": "object",
                "description": "上下文信息（可選）",
            },
            "metadata": {
                "type": "object",
                "description": "元數據（可選，包含 user_id、tenant_id 等）",
            },
        },
        "required": ["task_data"],
    },
    handler=execute_data_agent_task_handler,
)
