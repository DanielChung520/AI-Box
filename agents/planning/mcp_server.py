# 代碼功能說明: Planning Agent MCP Server 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Planning Agent MCP Server"""

from mcp.server.server import MCPServer
from agents.core.planning.agent import PlanningAgent
from agents.core.planning.models import PlanRequest

# 初始化 Planning Agent
planning_agent = PlanningAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="planning-agent",
    version="1.0.0",
)


# 註冊工具：生成計劃
async def generate_plan_handler(arguments: dict) -> dict:
    """生成計劃工具處理器"""
    request = PlanRequest(**arguments)
    result = planning_agent.generate_plan(request)
    return result.model_dump()


mcp_server.register_tool(
    name="generate_plan",
    description="生成任務執行計劃",
    input_schema={
        "type": "object",
        "properties": {
            "task": {
                "type": "string",
                "description": "任務描述",
            },
            "context": {
                "type": "object",
                "description": "上下文信息",
            },
            "requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "要求列表",
            },
            "constraints": {
                "type": "array",
                "items": {"type": "string"},
                "description": "約束條件列表",
            },
        },
        "required": ["task"],
    },
    handler=generate_plan_handler,
)
