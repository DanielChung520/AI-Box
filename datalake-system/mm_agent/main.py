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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 顯式加載 .env 文件
env_path = ai_box_root / ".env"
load_dotenv(dotenv_path=env_path)

from mm_agent.agent import MMAgent
from mm_agent.mcp_server import mcp_server
from mm_agent.chain.mm_agent_chain import MMAgentChain, MMChainInput
from mm_agent.translator import Translator
from mm_agent.negative_list import NegativeListChecker

from agents.services.protocol.base import AgentServiceRequest

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 檢查是否啟用語義轉譯
USE_SEMANTIC_TRANSLATOR = os.getenv("MM_AGENT_USE_SEMANTIC_TRANSLATOR", "false").lower() == "true"
logger.info(f"語義轉譯 Agent: {'啟用' if USE_SEMANTIC_TRANSLATOR else '禁用'}")

# 初始化Agent
mm_agent = MMAgent()
mm_chain = MMAgentChain(use_semantic_translator=USE_SEMANTIC_TRANSLATOR)
translator = Translator(use_semantic_translator=USE_SEMANTIC_TRANSLATOR)
negative_list = NegativeListChecker()

# 初始化 ReAct 引擎
from mm_agent.chain.react_executor import get_react_engine

_react_engine = get_react_engine()

# 創建FastAPI應用
app = FastAPI(
    title="MM-Agent Service",
    description="MM-Agent（庫管員Agent）服務 - 庫存管理業務Agent（LangChain + Ollama）",
    version="4.0.0",
)

# 配置 CORS（允許前端跨域訪問）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8503",  # Frontend React 開發服務
        "http://localhost:3000",  # 備選前端端口
        "http://127.0.0.1:8503",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        # 檢查是否是自然語言對話格式
        if "messages" in request and isinstance(request["messages"], list):
            # AI-Box 發送的對話格式
            # 提取最後一條用戶消息
            messages = request["messages"]
            last_user_msg = None
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    last_user_msg = msg.get("content", "")
                    break

            if last_user_msg:
                instruction = last_user_msg
                logger.info(f"[execute] 從對話中提取指令: {instruction}")

                # 構建 AgentServiceRequest
                agent_request = AgentServiceRequest(
                    task_id=request.get("task_id", "http-task"),
                    task_type="general_chat",  # 使用 general_chat 任務類型
                    task_data={
                        "instruction": instruction,
                        "user_id": request.get("user_id"),
                        "session_id": request.get("session_id"),
                    },
                    context=request.get("context"),
                    metadata=request.get("metadata"),
                )
            else:
                # 沒有找到用戶消息
                return {
                    "task_id": request.get("task_id", "http-task"),
                    "status": "error",
                    "result": None,
                    "error": "No user message found in messages",
                }
        else:
            # 原始結構化格式
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
        "features": ["LangChain", "Ollama", "MCP", "Negative List"],
    }


class ChatRequest(BaseModel):
    """對話請求 - 支持多輪對話"""

    instruction: str
    session_id: Optional[str] = None  # 對話會話 ID（多輪對話支持）
    user_id: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """對話響應 - 支持多輪對話"""

    success: bool
    response: str
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    session_id: Optional[str] = None  # 返回會話 ID
    resolved_query: Optional[str] = None  # 指代消解後的查詢
    translation: Optional[dict] = None
    debug_info: Optional[dict] = None


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat_v1(request: ChatRequest) -> ChatResponse:
    """對話端點 - ReAct 模式 + LangChain 混合編排

    流程：
    1. 判斷任務類型（單一查詢 / 操作指引 / 複合工作）
    2. 操作指引/複合工作 → 使用 ReAct 工作流程
    3. 單一查詢 → 使用原有的 mm_chain
    """
    try:
        instruction = request.instruction
        session_id = request.session_id or f"chat-{id(request)}"

        # 判斷任務類型
        is_guidance = any(
            kw in instruction
            for kw in [
                "如何",
                "怎麼",
                "步驟",
                "設置",
                "設定",
                "建立",
                "操作",
                "方法",
                "建議",
                "指導",
                "指引",
                "說明",
                "介紹",  # 知識/指引類
                "ABC",
                "abc",  # ABC 管理相關
            ]
        )
        is_compound = any(
            kw in instruction.lower() for kw in ["然後", "接著", "完成後", "最後", "並且", "以及"]
        )

        # 如果是操作指引或複合工作，使用 ReAct 引擎
        if is_guidance or is_compound:
            logger.info(f"[Chat] 使用 ReAct 工作流程: {instruction[:50]}...")

            # 啟動工作流程
            wf_result = await _react_engine.start_workflow(
                instruction=instruction,
                session_id=session_id,
                context=request.context,
            )

            if wf_result.get("success"):
                return ChatResponse(
                    success=True,
                    response=wf_result["response"],
                    needs_clarification=False,
                    clarification_message=None,
                    session_id=session_id,
                    resolved_query=None,
                    translation=None,
                    debug_info={
                        "step": "workflow_started",
                        "task_type": wf_result.get("task_type"),
                        "is_react_workflow": True,
                        "total_steps": len(wf_result.get("plan", {}).get("steps", [])),
                    },
                )

        # 預設使用原有的 mm_chain
        logger.info(f"[Chat] 使用 mm_chain: {instruction[:50]}...")

        input_data = MMChainInput(
            instruction=instruction,
            session_id=session_id,
            user_id=request.user_id,
            context=request.context,
        )

        result = await mm_chain.run(input_data)

        return ChatResponse(
            success=result.success,
            response=result.response,
            needs_clarification=result.needs_clarification,
            clarification_message=result.clarification_message,
            session_id=result.session_id,
            resolved_query=result.resolved_query,
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


@app.post("/api/v1/chat/execute-step")
async def execute_step(request: ChatRequest) -> dict:
    """對話端點 - 執行 ReAct 工作流程下一步

    用於多輪對話中執行複合工作的下一步
    """
    try:
        session_id = request.session_id
        if not session_id:
            return {"success": False, "error": "需要 session_id"}

        # 執行下一步
        result = await _react_engine.execute_next_step(
            session_id=session_id,
            user_response=request.instruction,
        )

        return {
            "success": result.success,
            "response": result.get("response", ""),
            "step_id": result.get("step_id"),
            "action_type": result.get("action_type"),
            "completed_steps": result.get("completed_steps", []),
            "total_steps": result.get("total_steps", 0),
            "waiting_for_user": result.get("waiting_for_user", False),
            "debug_info": result.get("debug_info", {}),
        }

    except Exception as e:
        logger.error(f"步驟執行失敗: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@app.get("/api/v1/chat/workflow/{session_id}")
async def get_chat_workflow_state(session_id: str) -> dict:
    """獲取對話工作流程狀態"""
    state = _react_engine.get_state(session_id)
    if state:
        return {"success": True, "state": state}
    return {"success": False, "error": "會話不存在"}


@app.delete("/api/v1/chat/workflow/{session_id}")
async def clear_chat_workflow_state(session_id: str) -> dict:
    """清除對話工作流程狀態"""
    _react_engine.clear_state(session_id)
    return {"success": True, "message": "狀態已清除"}


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
async def check_negative_list(request: ChatRequest) -> dict:
    """負面表列檢查端點"""
    try:
        denied, matched = negative_list.check(request.instruction)
        return {
            "success": True,
            "denied": denied,
            "matched_keywords": matched,
            "is_denied": denied,
        }
    except Exception as e:
        logger.error(f"負面表列檢查失敗: {e}")
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import uvicorn

    # 從環境變數獲取配置
    host = os.getenv("MM_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("MM_AGENT_SERVICE_PORT", "8003"))

    logger.info(f"啟動庫管員Agent服務: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
