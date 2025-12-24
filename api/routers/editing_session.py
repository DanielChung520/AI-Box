"""
代碼功能說明: 編輯 Session API - 支持 AI 編輯協議的 Session 管理和指令提交
創建日期: 2025-12-20 12:30:07 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:30:07 (UTC+8)
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

import structlog
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from api.core.response import APIResponse
from services.api.services.editing_session_service import get_editing_session_service
from system.security.dependencies import get_current_tenant_id, get_current_user
from system.security.models import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/editing", tags=["Editing Session"])


# ============================================================================
# Request/Response Models
# ============================================================================


class SessionStartRequest(BaseModel):
    """創建編輯 Session 請求"""

    doc_id: str = Field(..., description="文檔 ID")
    ttl_seconds: Optional[int] = Field(None, description="Session 過期時間（秒），默認 1 小時")


class SessionStartResponse(BaseModel):
    """創建編輯 Session 響應"""

    session_id: str = Field(..., description="Session ID")
    ws_url: Optional[str] = Field(None, description="WebSocket URL（如果支持流式傳輸）")


class EditingCommandRequest(BaseModel):
    """編輯指令請求"""

    session_id: str = Field(..., description="Session ID")
    command: str = Field(..., description="編輯指令")
    cursor_context: Optional[Dict[str, Any]] = Field(
        None,
        description="游標上下文信息",
        examples=[
            {
                "file": "main.py",
                "line": 45,
                "column": 10,
                "selection": "def hello(): pass",
            }
        ],
    )


class EditingCommandResponse(BaseModel):
    """編輯指令響應"""

    request_id: str = Field(..., description="編輯請求 ID（用於查詢狀態）")
    status: str = Field(..., description="請求狀態（queued/processing/completed/failed）")


# ============================================================================
# API Endpoints
# ============================================================================


@router.post("/session/start", status_code=status.HTTP_201_CREATED)
async def start_editing_session(
    body: SessionStartRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """創建新的編輯 Session

    用於初始化一個編輯會話，後續的編輯指令將通過此 Session 進行管理。
    """
    try:
        session_service = get_editing_session_service()

        session = session_service.create_session(
            doc_id=body.doc_id,
            user_id=current_user.user_id,
            tenant_id=tenant_id,
            ttl_seconds=body.ttl_seconds,
            metadata={"created_via": "api"},
        )

        # TODO: 生成 WebSocket URL（如果支持流式傳輸）
        ws_url = None  # 暫時為 None，待實現流式傳輸後更新

        response = SessionStartResponse(session_id=session.session_id, ws_url=ws_url)

        return APIResponse.success(
            data=response.model_dump(mode="json"),
            message="Editing session created",
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        logger.error("failed_to_create_editing_session", error=str(exc), doc_id=body.doc_id)
        return APIResponse.error(
            message=f"Failed to create editing session: {str(exc)}",
            error_code="SESSION_CREATE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/command", status_code=status.HTTP_202_ACCEPTED)
async def submit_editing_command(
    body: EditingCommandRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """提交編輯指令

    通過 Session 提交編輯指令，系統會將指令路由到 Agent 系統進行處理。
    """
    try:
        session_service = get_editing_session_service()

        # 驗證 Session
        session = session_service.get_session(session_id=body.session_id)
        if session is None:
            return APIResponse.error(
                message="Session not found or expired",
                error_code="SESSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 驗證用戶權限
        if session.user_id != current_user.user_id or session.tenant_id != tenant_id:
            return APIResponse.error(
                message="Session access denied",
                error_code="SESSION_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        # 集成到 Agent Orchestrator 系統
        try:
            from agents.services.protocol.base import AgentServiceRequest
            from agents.services.registry.registry import get_agent_registry

            registry = get_agent_registry()

            # 查找文檔編輯相關的 Agent
            # 優先查找 "document_editing" 類型的 Agent，如果沒有則使用 "execution" 類型
            agents = registry.list_agents(agent_type="document_editing")
            if not agents:
                agents = registry.list_agents(agent_type="execution")

            if not agents:
                # 如果沒有找到合適的 Agent，使用現有的 doc_edit API
                logger.warning(
                    "no_agent_found_for_editing",
                    session_id=body.session_id,
                    falling_back_to_doc_edit=True,
                )
                import uuid

                request_id = str(uuid.uuid4())
            else:
                # 使用第一個可用的 Agent
                agent = registry.get_agent(agents[0].agent_id)
                if not agent:
                    raise ValueError(f"Failed to get agent instance: {agents[0].agent_id}")

                # 構建 AgentServiceRequest
                # 將編輯指令轉換為 MCP Tool Call 格式
                task_data = {
                    "type": "document_editing",
                    "command": body.command,
                    "doc_id": session.doc_id,
                    "cursor_context": body.cursor_context or {},
                    "session_id": body.session_id,
                    "format": "search_replace",  # 指定使用 Search-and-Replace 格式
                }

                service_request = AgentServiceRequest(
                    task_id=f"editing_{body.session_id}_{int(time.time())}",
                    task_type="document_editing",
                    task_data=task_data,
                    context={
                        "session_id": body.session_id,
                        "doc_id": session.doc_id,
                        "user_id": current_user.user_id,
                        "tenant_id": tenant_id,
                    },
                    metadata={
                        "session_id": body.session_id,
                        "created_via": "editing_session_api",
                    },
                )

                # 執行任務
                service_response = await agent.execute(service_request)
                request_id = service_response.task_id

                # 處理響應
                if service_response.status == "error":
                    logger.error(
                        "agent_execution_failed",
                        session_id=body.session_id,
                        request_id=request_id,
                        error=service_response.error,
                    )
                    return APIResponse.error(
                        message=f"Agent execution failed: {service_response.error}",
                        error_code="AGENT_EXECUTION_FAILED",
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

                # 如果 Agent 返回了 Search-and-Replace 格式的結果，可以進一步處理
                # 將 request_id 存儲到 Session metadata 中，供流式傳輸使用
                if service_response.result:
                    logger.info(
                        "agent_execution_success",
                        session_id=body.session_id,
                        request_id=request_id,
                        has_result=bool(service_response.result),
                    )
                    # 更新 Session metadata，存儲 request_id 和結果
                    session_service.update_session(
                        session_id=body.session_id,
                        metadata={
                            "last_request_id": request_id,
                            "last_result": service_response.result,
                        },
                    )
        except ImportError:
            # 如果 Agent 系統不可用，使用現有的 doc_edit API
            logger.warning(
                "agent_system_unavailable",
                session_id=body.session_id,
                falling_back_to_doc_edit=True,
            )
            import uuid

            request_id = str(uuid.uuid4())
        except Exception as exc:
            logger.error(
                "agent_integration_failed",
                session_id=body.session_id,
                error=str(exc),
                falling_back_to_doc_edit=True,
            )
            # 如果 Agent 集成失敗，使用現有的 doc_edit API 作為後備
            import uuid

            request_id = str(uuid.uuid4())

        # 更新 Session（延長 TTL）
        session_service.update_session(session_id=body.session_id, extend_ttl=True)

        response = EditingCommandResponse(
            request_id=request_id,
            status="queued",  # 暫時返回 queued，實際應該根據 Agent 系統狀態返回
        )

        logger.info(
            "editing_command_submitted",
            session_id=body.session_id,
            request_id=request_id,
            command=body.command[:100],  # 只記錄前 100 字符
        )

        return APIResponse.success(
            data=response.model_dump(mode="json"),
            message="Editing command submitted",
            status_code=status.HTTP_202_ACCEPTED,
        )
    except Exception as exc:
        logger.error(
            "failed_to_submit_editing_command",
            error=str(exc),
            session_id=body.session_id,
        )
        return APIResponse.error(
            message=f"Failed to submit editing command: {str(exc)}",
            error_code="COMMAND_SUBMIT_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/session/{session_id}", status_code=status.HTTP_200_OK)
async def get_session_status(
    session_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """獲取 Session 狀態"""
    try:
        session_service = get_editing_session_service()

        session = session_service.get_session(session_id=session_id)
        if session is None:
            return APIResponse.error(
                message="Session not found or expired",
                error_code="SESSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 驗證用戶權限
        if session.user_id != current_user.user_id or session.tenant_id != tenant_id:
            return APIResponse.error(
                message="Session access denied",
                error_code="SESSION_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return APIResponse.success(
            data=session.to_dict(),
            message="Session status retrieved",
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error("failed_to_get_session_status", error=str(exc), session_id=session_id)
        return APIResponse.error(
            message=f"Failed to get session status: {str(exc)}",
            error_code="SESSION_GET_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/session/{session_id}", status_code=status.HTTP_200_OK)
async def delete_session(
    session_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(get_current_user),
) -> JSONResponse:
    """刪除 Session"""
    try:
        session_service = get_editing_session_service()

        session = session_service.get_session(session_id=session_id)
        if session is None:
            return APIResponse.error(
                message="Session not found",
                error_code="SESSION_NOT_FOUND",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 驗證用戶權限
        if session.user_id != current_user.user_id or session.tenant_id != tenant_id:
            return APIResponse.error(
                message="Session access denied",
                error_code="SESSION_ACCESS_DENIED",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        deleted = session_service.delete_session(session_id=session_id)
        if not deleted:
            return APIResponse.error(
                message="Failed to delete session",
                error_code="SESSION_DELETE_FAILED",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return APIResponse.success(
            data={"session_id": session_id, "deleted": True},
            message="Session deleted",
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        logger.error("failed_to_delete_session", error=str(exc), session_id=session_id)
        return APIResponse.error(
            message=f"Failed to delete session: {str(exc)}",
            error_code="SESSION_DELETE_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
