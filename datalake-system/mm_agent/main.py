# 代碼功能說明: 庫管員Agent服務主程序
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""庫管員Agent服務主程序 - FastAPI應用 + MCP + LangChain"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 顯式加載 .env 文件
env_path = ai_box_root / ".env"
load_dotenv(dotenv_path=env_path)

from mm_agent.agent import MMAgent
from mm_agent.mcp_server import mcp_server
from mm_agent.chain.mm_agent_chain import MMAgentChain, MMChainInput
from mm_agent.translator import Translator
from mm_agent.positive_list import PositiveListChecker

from agents.services.protocol.base import AgentServiceRequest

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 初始化Agent
mm_agent = MMAgent()
mm_chain = MMAgentChain()
translator = Translator()
positive_list = PositiveListChecker()

# 創建FastAPI應用
app = FastAPI(
    title="MM-Agent Service",
    description="MM-Agent（庫管員Agent）服務 - 庫存管理業務Agent（LangChain + Ollama）",
    version="4.0.0",
)


# 集成 MCP Server 到 FastAPI 應用
# 直接使用 MCP Server 的 FastAPI 應用實例
from fastapi import Request

from mcp.server.protocol.models import MCPError, MCPErrorResponse, MCPRequest


@app.post("/mcp")
async def handle_mcp_request(request: Request):
    """處理 MCP 請求（/mcp 端點）"""
    return await _handle_mcp_request_internal(request)


@app.post("/")
async def handle_mcp_root(request: Request):
    """處理 MCP 請求（根路徑，用於 Cloudflare Tunnel）"""
    return await _handle_mcp_request_internal(request)


async def _handle_mcp_request_internal(request: Request):
    """處理 MCP 請求"""
    body = None

    try:
        body = await request.json()
        mcp_request = MCPRequest(**body)
        response = await mcp_server._handle_request(mcp_request)
        return JSONResponse(content=response.model_dump(exclude_none=True))
    except Exception as e:
        logger.error(f"Error handling MCP request: {e}", exc_info=True)
        error_response = MCPErrorResponse(
            id=body.get("id") if body else None,
            error=MCPError(
                code=-32603,
                message="Internal error",
                data={"error": str(e)},
            ),
        )
        return JSONResponse(
            content=error_response.model_dump(exclude_none=True),
            status_code=500,
        )


@app.get("/health")
async def health_check() -> dict:
    """健康檢查端點"""
    try:
        status = await mm_agent.health_check()
        return {
            "status": "healthy",
            "agent_status": status.value if hasattr(status, "value") else str(status),
        }
    except Exception as e:
        logger.error(f"健康檢查失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")


@app.get("/capabilities")
async def get_capabilities() -> dict:
    """獲取服務能力端點"""
    try:
        capabilities = await mm_agent.get_capabilities()
        return capabilities
    except Exception as e:
        logger.error(f"獲取服務能力失敗: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get capabilities: {e}")


@app.post("/execute")
async def execute(request: dict) -> dict:
    """執行任務端點"""
    try:
        # 構建AgentServiceRequest
        agent_request = AgentServiceRequest(
            task_id=request.get("task_id", "http-task"),
            task_type=request.get("task_type", "warehouse_management"),
            task_data=request.get("task_data", {}),
            context=request.get("context"),
            metadata=request.get("metadata"),
        )

        # 調用Agent
        response = await mm_agent.execute(agent_request)

        # 返回結果
        if hasattr(response, "model_dump"):
            return response.model_dump()
        elif hasattr(response, "dict"):
            return response.dict()
        else:
            return response  # type: ignore[return-value]

    except Exception as e:
        logger.error(f"執行任務失敗: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "task_id": request.get("task_id", "http-task"),
                "status": "error",
                "result": None,
                "error": str(e),
            },
        )


@app.get("/")
async def root() -> dict:
    """根端點"""
    return {
        "service": "MM-Agent Service",
        "version": "4.0.0",
        "status": "running",
        "features": ["LangChain", "Ollama", "MCP", "Positive List"],
    }


class ChatRequest(BaseModel):
    """對話請求"""

    instruction: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """對話響應"""

    success: bool
    response: str
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    translation: Optional[dict] = None
    debug_info: Optional[dict] = None


@app.post("/api/v1/mm-agent/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """對話端點 - 使用 LangChain 編排"""
    try:
        input_data = MMChainInput(
            instruction=request.instruction,
            context=request.context,
        )

        result = mm_chain.run(input_data)

        return ChatResponse(
            success=result.success,
            response=result.response,
            needs_clarification=result.needs_clarification,
            clarification_message=result.clarification_message,
            translation=result.translation.model_dump() if result.translation else None,
            debug_info=result.debug_info,
        )

    except Exception as e:
        logger.error(f"對話執行失敗: {e}", exc_info=True)
        return ChatResponse(
            success=False,
            response="",
            clarification_message=f"執行錯誤: {str(e)}",
        )


@app.post("/api/v1/mm-agent/translate")
async def translate(request: ChatRequest) -> dict:
    """轉譯端點 - 專業術語轉換"""
    try:
        translation = translator.translate(request.instruction)
        return {
            "success": True,
            "translation": translation.model_dump(),
        }
    except Exception as e:
        logger.error(f"轉譯失敗: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/v1/mm-agent/check")
async def check_positive_list(request: ChatRequest) -> dict:
    """正面表列檢查端點"""
    try:
        passed, matched = positive_list.check(request.instruction)
        return {
            "success": True,
            "passed": passed,
            "matched_keywords": matched,
            "needs_clarification": not passed,
        }
    except Exception as e:
        logger.error(f"正面表列檢查失敗: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    # 從環境變數獲取配置
    host = os.getenv("MM_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("MM_AGENT_SERVICE_PORT", "8003"))

    logger.info(f"啟動庫管員Agent服務: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
