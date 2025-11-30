# 代碼功能說明: Execution Agent MCP Server 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Execution Agent MCP Server"""

from mcp.server.server import MCPServer
from agents.execution.agent import ExecutionAgent
from agents.execution.models import ExecutionRequest

# 初始化 Execution Agent
execution_agent = ExecutionAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="execution-agent",
    version="1.0.0",
)


# 註冊工具：執行任務
async def execute_task_handler(arguments: dict) -> dict:
    """執行任務工具處理器"""
    request = ExecutionRequest(**arguments)
    result = execution_agent.execute(request)
    return result.model_dump()


mcp_server.register_tool(
    name="execute_task",
    description="執行任務或工具調用",
    input_schema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "任務描述",
            },
            "tool_name": {
                "type": "string",
                "description": "工具名稱（可選）",
            },
            "tool_args": {
                "type": "object",
                "description": "工具參數（可選）",
            },
            "plan_step_id": {
                "type": "string",
                "description": "計劃步驟ID（可選）",
            },
            "context": {
                "type": "object",
                "description": "上下文信息（可選）",
            },
        },
        "required": ["task"],
    },
    handler=execute_task_handler,
)
