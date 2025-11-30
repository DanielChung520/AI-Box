# 代碼功能說明: Review Agent MCP Server 實現
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""Review Agent MCP Server"""

from mcp.server.server import MCPServer
from agents.review.agent import ReviewAgent
from agents.review.models import ReviewRequest

# 初始化 Review Agent
review_agent = ReviewAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="review-agent",
    version="1.0.0",
)


# 註冊工具：審查結果
async def review_result_handler(arguments: dict) -> dict:
    """審查結果工具處理器"""
    request = ReviewRequest(**arguments)
    result = review_agent.review(request)
    return result.model_dump()


mcp_server.register_tool(
    name="review_result",
    description="審查執行結果並生成反饋",
    input_schema={
        "type": "object",
        "properties": {
            "result": {
                "type": "object",
                "description": "執行結果",
            },
            "expected": {
                "type": "object",
                "description": "預期結果（可選）",
            },
            "criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "審查標準列表（可選）",
            },
            "context": {
                "type": "object",
                "description": "上下文信息（可選）",
            },
        },
        "required": ["result"],
    },
    handler=review_result_handler,
)
