# 代碼功能說明: 庫管員Agent服務主程序
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31

"""庫管員Agent服務主程序 - FastAPI應用 + MCP + LangChain"""

import logging
import os
import sys
import json
from pathlib import Path
from typing import Optional
from sse_starlette.sse import EventSourceResponse

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 全局字典：存儲待執行的工作流（從 WebSocket 生成計劃後，用戶確認時使用）
PENDING_WORKFLOWS: dict = {}

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
        "*",  # 允許所有來源（WebSocket）
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
    metadata: Optional[dict] = None  # 擴展元數據（如意圖分類結果）


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
                plan = wf_result.get("plan", {})
                thought_process = plan.get("thought_process", "") if isinstance(plan, dict) else ""

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
                        "total_steps": len(plan.get("steps", [])) if isinstance(plan, dict) else 0,
                        "thought_process": thought_process,
                        "plan": plan if isinstance(plan, dict) else None,
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
            "success": result.get("success", False),
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


@app.post("/api/v1/chat/auto-execute")
async def auto_execute_workflow(request: ChatRequest) -> dict:
    """自動執行工作流所有步驟

    無需等待用戶確認，直接執行所有步驟
    """
    try:
        session_id = request.session_id
        if not session_id:
            return {"success": False, "error": "需要 session_id"}

        result = await _react_engine.execute_all_steps(
            session_id=session_id,
            user_response=request.instruction,
            instruction=request.instruction,
        )

        return {
            "success": result.get("success", False),
            "response": result.get("final_response", ""),
            "responses": result.get("responses", []),
            "completed_steps": result.get("completed_steps", []),
            "total_steps": result.get("total_steps", 0),
            "debug_info": {
                "step": "auto_executed",
                "all_results": result.get("all_results", []),
            },
        }

    except Exception as e:
        logger.error(f"自動執行失敗: {e}", exc_info=True)
        return {"success": False, "error": str(e)}



@app.get("/api/v1/chat/stream")
async def chat_stream_get(sid: str, instruction: str):
    """串流對話端點 - 思考過程即時顯示 (GET)

    流程：
    1. 調用 Ollama 串流
    2. 解析 <thinking> 標籤
    3. 透過 SSE 即時發送思考過程到前端
    """
    from mm_agent.stream_endpoint import generate_stream

    session_id = sid or f"stream-{id(None)}"

    return await generate_stream(instruction, session_id)


@app.post("/api/v1/chat/stream")
async def chat_stream_post(request: ChatRequest):
    """串流對話端點 - 思考過程即時顯示 (POST)

    流程：
    1. 調用 Ollama 串流
    2. 解析 <thinking> 標籤
    3. 透過 SSE 即時發送思考過程到前端
    """
    from mm_agent.stream_endpoint import generate_stream

    instruction = request.instruction
    session_id = request.session_id or f"stream-{id(request)}"

    return await generate_stream(instruction, session_id)

    return generate_stream(instruction, session_id)


@app.websocket("/api/v1/chat/ws")
async def websocket_chat(websocket: WebSocket):
    """WebSocket 串流端點 - 更可靠的實時通信"""
    from mm_agent.websocket_endpoint import websocket_generate_stream
    
    # 允許所有 WebSocket 連接（解決 CORS 問題）
    await websocket.accept()
    await websocket_generate_stream(websocket)


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


@app.post("/api/v1/chat/intent")
async def classify_intent(request: ChatRequest) -> dict:
    """意圖分類端點

    流程：
    1. 檢查是否有進行中的工作流（session_id 存在且 waiting_for_user=True）
    2. 如果是延續對話，直接執行下一步
    3. 如果是新對話，進行意圖分類
    """
    from mm_agent.intent_endpoint import classify_intent as llm_classify_intent

    try:
        instruction = request.instruction
        session_id = request.session_id or f"intent-{id(request)}"

        logger.info(f"[Intent] 收到請求: instruction='{instruction[:50]}...', session_id='{session_id}'")

        # 檢查工作流狀態
        all_workflows = list(_react_engine._workflows.keys()) if hasattr(_react_engine, '_workflows') else []
        logger.info(f"[Intent] 所有工作流: {all_workflows}")
        
        # 檢查 PENDING_WORKFLOWS（從 SSE/WebSocket 生成的計劃）
        try:
            from mm_agent.main import PENDING_WORKFLOWS
            pending_keys = list(PENDING_WORKFLOWS.keys())
            logger.info(f"[Intent] 待執行工作流 (PENDING_WORKFLOWS): {pending_keys}")
        except Exception as e:
            logger.error(f"[Intent] 讀取 PENDING_WORKFLOWS 失敗: {e}")
            pending_keys = []

        # 檢查是否有進行中的工作流（用戶回覆場景）
        if session_id:
            # 首先檢查 PENDING_WORKFLOWS（從 SSE/WebSocket 生成的計劃）
            if session_id in PENDING_WORKFLOWS:
                pending = PENDING_WORKFLOWS.pop(session_id)
                logger.info(f"[Intent] 找到待執行工作流，開始執行: {pending.get('instruction', '')[:50]}...")

                # 啟動工作流
                wf_result = await _react_engine.start_workflow(
                    instruction=pending["instruction"],
                    session_id=session_id,
                    context={"original_plan": pending.get("plan")}
                )

                if wf_result.get("success"):
                    return {
                        "success": True,
                        "intent": "CONTINUE_WORKFLOW",
                        "confidence": 1.0,
                        "is_simple_query": False,
                        "needs_clarification": False,
                        "missing_fields": [],
                        "clarification_prompts": {},
                        "thought_process": "已啟動工作流，開始執行第一步",
                        "session_id": session_id,
                        "workflow_result": wf_result,
                    }
                else:
                    logger.error(f"[Intent] 啟動工作流失敗: {wf_result}")

            # 檢查 _react_engine 中的現有工作流
            state = _react_engine.get_state(session_id)
            logger.info(f"[Intent] 查詢工作流狀態: session={session_id}, state={state}")

            if state:
                # 有進行中的工作流，檢查是否在等待用戶回覆
                current_step = state.get("current_step", 0)
                completed_steps = state.get("completed_steps", [])
                total_steps = state.get("total_steps", 0)

                logger.info(f"[Intent] 工作流狀態: current_step={current_step}, total_steps={total_steps}")

                # 如果還有步驟未完成，視為用戶回覆，繼續執行
                if current_step < total_steps:
                    logger.info(f"[Intent] 檢測到進行中的工作流，session={session_id}，執行下一步")

                    # 直接執行下一步，將用戶回覆傳入
                    step_result = await _react_engine.execute_next_step(
                        session_id=session_id,
                        user_response=instruction,
                    )

                    if step_result.get("success"):
                        return {
                            "success": True,
                            "intent": "CONTINUE_WORKFLOW",
                            "confidence": 1.0,
                            "is_simple_query": False,
                            "needs_clarification": False,
                            "missing_fields": [],
                            "clarification_prompts": {},
                            "thought_process": "檢測到進行中的工作流，直接執行下一步",
                            "session_id": session_id,
                            "workflow_result": step_result,
                        }

        # 沒有進行中的工作流，進行意圖分類
        result = await llm_classify_intent(instruction, session_id)

        return {
            "success": True,
            "intent": result.intent.value,
            "confidence": result.confidence,
            "is_simple_query": result.is_simple_query,
            "needs_clarification": result.needs_clarification,
            "missing_fields": result.missing_fields,
            "clarification_prompts": result.clarification_prompts,
            "thought_process": result.thought_process,
            "session_id": session_id,
        }
    except Exception as e:
        logger.error(f"意圖分類失敗: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "intent": "SIMPLE_QUERY",
            "confidence": 0.5,
            "is_simple_query": True,
            "needs_clarification": False,
        }


@app.get("/api/v1/chat/intent")
async def classify_intent_get(sid: str, instruction: str):
    """意圖分類端點 - GET 方法

    流程：
    1. 檢查是否有進行中的工作流（session_id 存在且 waiting_for_user=True）
    2. 如果是延續對話，直接執行下一步
    3. 如果是新對話，進行意圖分類
    """
    from mm_agent.intent_endpoint import classify_intent as llm_classify_intent

    session_id = sid or f"intent-{id(None)}"

    # 檢查是否有進行中的工作流（用戶回覆場景）
    if session_id and sid:
        state = _react_engine.get_state(session_id)
        if state:
            # 有進行中的工作流，檢查是否在等待用戶回覆
            current_step = state.get("current_step", 0)
            total_steps = state.get("total_steps", 0)

            # 如果還有步驟未完成，視為用戶回覆，繼續執行
            if current_step < total_steps:
                logger.info(f"[Intent] 檢測到進行中的工作流，session={session_id}，執行下一步")

                # 直接執行下一步，將用戶回覆傳入
                step_result = await _react_engine.execute_next_step(
                    session_id=session_id,
                    user_response=instruction,
                )

                if step_result.get("success"):
                    return {
                        "success": True,
                        "intent": "CONTINUE_WORKFLOW",
                        "confidence": 1.0,
                        "is_simple_query": False,
                        "needs_clarification": False,
                        "missing_fields": [],
                        "clarification_prompts": {},
                        "thought_process": "檢測到進行中的工作流，直接執行下一步",
                        "session_id": session_id,
                        "workflow_result": step_result,
                    }

    # 沒有進行中的工作流，進行意圖分類
    result = await llm_classify_intent(instruction, session_id)

    return {
        "success": True,
        "intent": result.intent.value,
        "confidence": result.confidence,
        "is_simple_query": result.is_simple_query,
        "needs_clarification": result.needs_clarification,
        "missing_fields": result.missing_fields,
        "clarification_prompts": result.clarification_prompts,
        "thought_process": result.thought_process,
        "session_id": session_id,
    }


@app.post("/api/v1/chat/intent/stream")
async def classify_intent_stream(request: ChatRequest):
    """意圖分類 SSE 串流端點

    流程：
    1. 檢查是否有進行中的工作流（session_id 存在且 waiting_for_user=True）
    2. 如果是延續對話，發送特殊事件通知前端
    3. 如果是新對話，進行意圖分類 SSE 串流
    """
    from mm_agent.intent_endpoint import generate_intent_stream
    import json
    from sse_starlette.sse import EventSourceResponse

    instruction = request.instruction
    session_id = request.session_id or f"intent-{id(request)}"

    # 檢查是否有進行中的工作流（用戶回覆場景）
    if session_id and request.session_id:
        state = _react_engine.get_state(session_id)
        if state:
            current_step = state.get("current_step", 0)
            total_steps = state.get("total_steps", 0)

            if current_step < total_steps:
                logger.info(f"[Intent Stream] 檢測到進行中的工作流，session={session_id}")

                async def workflow_continue_generator():
                    # 發送事件通知前端繼續工作流
                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "workflow_continue",
                            "message": "檢測到進行中的工作流，正在執行下一步...",
                            "session_id": session_id,
                        }),
                    }

                    # 執行下一步
                    step_result = await _react_engine.execute_next_step(
                        session_id=session_id,
                        user_response=instruction,
                    )

                    if step_result.get("success"):
                        yield {
                            "event": "message",
                            "data": json.dumps({
                                "type": "workflow_step_completed",
                                "response": step_result.get("response", ""),
                                "waiting_for_user": step_result.get("waiting_for_user", False),
                                "completed_steps": step_result.get("completed_steps", []),
                                "total_steps": step_result.get("total_steps", 0),
                                "session_id": session_id,
                            }),
                        }

                    yield {
                        "event": "message",
                        "data": json.dumps({
                            "type": "complete",
                            "message": "完成",
                            "session_id": session_id,
                        }),
                    }

                return EventSourceResponse(workflow_continue_generator(), media_type="text/event-stream")

    # 沒有進行中的工作流，進行意圖分類 SSE 串流
    return await generate_intent_stream(instruction, session_id)


@app.post("/api/v1/chat/knowledge")
async def knowledge_query(request: ChatRequest) -> dict:
    """知識查詢端點

    處理 KNOWLEDGE_QUERY 意圖，調用 KA-Agent 或 LLM 回退

    Args:
        request: 聊天請求

    Returns:
        知識查詢結果
    """
    from mm_agent.knowledge_service import get_knowledge_service, KnowledgeSourceType

    try:
        instruction = request.instruction
        session_id = request.session_id or f"knowledge-{id(request)}"

        # 從意圖分類結果中獲取來源類型
        # 如果沒有來源類型，預設為 external
        source_type_str = request.metadata.get("knowledge_source_type", "external") if request.metadata else "external"
        try:
            source_type = KnowledgeSourceType(source_type_str)
        except ValueError:
            source_type = KnowledgeSourceType.EXTERNAL

        knowledge_service = get_knowledge_service()
        result = await knowledge_service.query(
            query=instruction,
            source_type=source_type,
            session_id=session_id,
        )

        # 格式化回覆
        answer = result.answer
        if result.sources:
            sources_text = "\n\n**參考來源：**\n"
            for s in result.sources[:3]:
                if isinstance(s, dict):
                    sources_text += f"- {s.get('title', s.get('source', '未知來源'))}\n"
                else:
                    sources_text += f"- {s}\n"
            answer += sources_text

        return {
            "success": result.success,
            "answer": answer,
            "sources": result.sources,
            "source_type": result.source_type.value,
            "query_time_ms": result.query_time_ms,
            "error": result.error,
            "session_id": session_id,
        }

    except Exception as e:
        logger.error(f"知識查詢失敗: {e}", exc_info=True)
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "source_type": "unknown",
            "query_time_ms": 0,
            "error": str(e),
            "session_id": request.session_id or f"knowledge-{id(request)}",
        }


@app.get("/api/v1/chat/knowledge")
async def knowledge_query_get(sid: str, query: str, source_type: str = "external"):
    """知識查詢端點 - GET 方法

    Args:
        sid: 會話 ID
        query: 查詢問題
        source_type: 知識來源類型 (internal/external)

    Returns:
        知識查詢結果
    """
    from mm_agent.knowledge_service import get_knowledge_service, KnowledgeSourceType

    try:
        try:
            st = KnowledgeSourceType(source_type)
        except ValueError:
            st = KnowledgeSourceType.EXTERNAL

        knowledge_service = get_knowledge_service()
        result = await knowledge_service.query(
            query=query,
            source_type=st,
            session_id=sid,
        )

        answer = result.answer
        if result.sources:
            sources_text = "\n\n**參考來源：**\n"
            for s in result.sources[:3]:
                if isinstance(s, dict):
                    sources_text += f"- {s.get('title', s.get('source', '未知來源'))}\n"
                else:
                    sources_text += f"- {s}\n"
            answer += sources_text

        return {
            "success": result.success,
            "answer": answer,
            "sources": result.sources,
            "source_type": result.source_type.value,
            "query_time_ms": result.query_time_ms,
            "error": result.error,
            "session_id": sid,
        }

    except Exception as e:
        logger.error(f"知識查詢失敗: {e}", exc_info=True)
        return {
            "success": False,
            "answer": "",
            "sources": [],
            "source_type": "unknown",
            "query_time_ms": 0,
            "error": str(e),
            "session_id": sid,
        }


if __name__ == "__main__":
    import uvicorn

    # 從環境變數獲取配置
    host = os.getenv("MM_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("MM_AGENT_SERVICE_PORT", "8003"))

    logger.info(f"啟動庫管員Agent服務: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
