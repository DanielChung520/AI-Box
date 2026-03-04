#!/usr/bin/env python3
"""修复 MM-Agent Data-Agent v5 响应处理"""

import re

with open("mm_agent/agent.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. 修改端点
content = content.replace('+ "/api/v1/data-agent/jp/execute"', '+ "/api/v1/data-agent/v5/execute"')

# 2. 修改 _execute_responsibility 调用
content = content.replace(
    "result = await self._execute_responsibility(responsibility, semantic_result, request)",
    "result = await self._execute_responsibility(responsibility, semantic_result, request, user_instruction)",
)

# 3. 修改 _execute_responsibility 签名
content = content.replace(
    "async def _execute_responsibility(\n        self,\n        responsibility: Any,\n        semantic_result: Any,\n        request: AgentServiceRequest,\n    ) -> Dict[str, Any]:",
    'async def _execute_responsibility(\n        self,\n        responsibility: Any,\n        semantic_result: Any,\n        request: AgentServiceRequest,\n        user_instruction: str = "",\n    ) -> Dict[str, Any]:',
)

# 4. 修改 _query_stock_info 调用
content = content.replace(
    "return await self._query_stock_info(parameters, request)",
    "return await self._query_stock_info(parameters, request, user_instruction)",
)

# 5. 修改 _query_stock_info 签名
content = content.replace(
    "async def _query_stock_info(\n        self,\n        parameters: Dict[str, Any],\n        request: AgentServiceRequest,\n    ) -> Dict[str, Any]:",
    'async def _query_stock_info(\n        self,\n        parameters: Dict[str, Any],\n        request: AgentServiceRequest,\n        user_instruction: str = "",\n    ) -> Dict[str, Any]:',
)

# 6. 修改响应处理逻辑
old_logic = """            # 1. 查無資料 (NO_DATA_FOUND) - 交由 LLM 業務回覆
            if result.get("status") == "success":
                data_result = result.get("result", {})
                rows = data_result.get("data", [])"""

new_logic = """            # 1. 查询成功 - Data-Agent v5 返回 success: true 或 status: "success"
            if result.get("success") == True or result.get("status") == "success":
                # Data-Agent v5: result directly contains data
                data_result = result if result.get("data") else result.get("result", {})
                rows = data_result.get("data", [])"""

content = content.replace(old_logic, new_logic)

with open("mm_agent/agent.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done!")
