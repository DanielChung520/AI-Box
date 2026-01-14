# 代碼功能說明: 庫管員Agent MCP Server實現
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""庫管員Agent MCP Server"""

# 導入庫管員Agent（在 datalake-system 中）
import sys
from pathlib import Path

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

# 導入 AI-Box 項目的模塊
import sys
from pathlib import Path

from warehouse_manager_agent.agent import WarehouseManagerAgent

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from agents.services.protocol.base import AgentServiceRequest
from mcp.server.server import MCPServer

# 初始化庫管員Agent
warehouse_agent = WarehouseManagerAgent()

# 創建 MCP Server
mcp_server = MCPServer(
    name="warehouse-manager-agent",
    version="1.0.0",
)


# 註冊工具：執行庫存管理任務
async def execute_warehouse_agent_task_handler(arguments: dict) -> dict:
    """執行庫存管理任務工具處理器"""
    try:
        # 構建 AgentServiceRequest
        request = AgentServiceRequest(
            task_id=arguments.get("task_id", "mcp-task"),
            task_type=arguments.get("task_type", "warehouse_management"),
            task_data=arguments.get("task_data", {}),
            context=arguments.get("context"),
            metadata=arguments.get("metadata"),
        )

        # 調用庫管員Agent
        result = await warehouse_agent.execute(request)

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
    name="warehouse_execute_task",
    description="執行庫存管理任務（查詢料號、查詢庫存、缺料分析、生成採購單等）",
    input_schema={
        "type": "object",
        "properties": {
            "task_id": {
                "type": "string",
                "description": "任務 ID（可選）",
            },
            "task_type": {
                "type": "string",
                "description": "任務類型（可選，默認：warehouse_management）",
            },
            "task_data": {
                "type": "object",
                "description": "任務數據（必需），包含 instruction 字段",
                "properties": {
                    "instruction": {
                        "type": "string",
                        "description": "用戶指令（自然語言），例如：'查詢料號 ABC-123 的庫存'",
                    },
                },
                "required": ["instruction"],
            },
            "context": {
                "type": "object",
                "description": "上下文信息（可選）",
            },
            "metadata": {
                "type": "object",
                "description": "元數據（可選，包含 user_id、tenant_id、session_id 等）",
            },
        },
        "required": ["task_data"],
    },
    handler=execute_warehouse_agent_task_handler,
)
