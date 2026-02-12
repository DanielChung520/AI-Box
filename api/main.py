# 代碼功能說明: FastAPI 應用主入口
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 00:06 UTC+8
# ruff: noqa: E402

"""FastAPI 應用主入口文件"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 加載環境變數（在導入其他模組之前）
# 修改時間：2025-01-27 - 確保 .env 文件在應用啟動時被加載
project_root = Path(__file__).parent.parent
env_file = project_root / ".env"
if env_file.exists():
    load_dotenv(env_file, override=True)

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.middleware.error_handler import ErrorHandlerMiddleware
from api.middleware.logging import LoggingMiddleware
from api.middleware.request_id import RequestIDMiddleware

# WBS-2.4: 監控與日誌 - Prometheus 中間件
try:
    from services.api.middleware.prometheus import PrometheusMiddleware

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus 中間件不可用")
# 可選導入 governance 路由
from types import ModuleType
from typing import Optional

# OAuth2 和監控代理路由
oauth2_router: Optional[ModuleType] = None
monitoring_proxy_router: Optional[ModuleType] = None

try:
    from api.routers import oauth2_router

    logging.info("OAuth2 SSO router imported successfully")
except ImportError as e:
    logging.warning(f"OAuth2 SSO router import failed: {e}")
    oauth2_router = None

try:
    from api.routers import monitoring_proxy_router

    logging.info("Monitoring proxy router imported successfully")
except ImportError as e:
    logging.warning(f"Monitoring proxy router import failed: {e}")
    monitoring_proxy_router = None

from api.core.version import API_PREFIX, get_version_info
from api.routers import (
    agent_auth,
    agent_catalog,
    agent_category,
    agent_display_config,
    agent_files,
    agent_registration,
    agent_registry,
    agent_secret,
    agent_status,
    agents,
    alert_webhook,
    audit_log,
    auth,
    chat,
    chat_module,
    config_definitions,
    data_consent,
    execution,
    file_management,
    file_metadata,
    file_upload,
    health,
    # knowledge_ontology,  # 註釋掉：檔案位置錯誤導致循環引用
    llm_models,
    mcp,
    moe,
    moe_metrics,
    ontology,
    orchestrator,
    planning,
    prometheus_compat,
    reports,
    review,
    rq_monitor,
    security_group,
    service_alert,
    service_monitor,
    system_admin,
    system_config,
    task_analyzer,
    user_account,
    user_sessions,
    user_tasks,
)

# 修改時間：2025-12-08 12:30:00 UTC+8 - 使用統一的日誌配置模組
# 修改時間：2026-01-28 10:30:00 UTC+8 - 添加 Agent 日誌配置
from system.logging_config import setup_agent_logging, setup_fastapi_logging
from system.security.config import get_security_settings
from system.security.middleware import SecurityMiddleware

# 配置 FastAPI 日誌（使用 RotatingFileHandler，最大 500KB，保留 4 個備份）
setup_fastapi_logging()

# 配置 Agent 日誌（獨立於 FastAPI 日誌，便於追蹤和調試）
setup_agent_logging()

logger = logging.getLogger(__name__)

# 可選導入 CrewAI 路由（如果模組未安裝則跳過）
try:
    from api.routers import crewai, crewai_tasks

    CREWAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CrewAI 路由不可用: {e}")
    CREWAI_AVAILABLE = False
    crewai = None  # type: ignore[assignment]
    crewai_tasks = None  # type: ignore[assignment]

# 獲取版本信息
version_info = get_version_info()

# 創建 FastAPI 應用
app = FastAPI(
    title="AI Box API Gateway",
    version=version_info["version"],
    description="AI Box 統一 API 入口 - 提供 Agent 管理、任務分析、協調等功能",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    tags_metadata=[
        {
            "name": "Health",
            "description": "健康檢查和服務狀態端點",
        },
        {
            "name": "Agents",
            "description": "Agent 管理和執行相關操作",
        },
        {
            "name": "Task Analyzer",
            "description": "任務分析和分類功能",
        },
        {
            "name": "Agent Orchestrator",
            "description": "Agent 協調和任務分發功能",
        },
        {
            "name": "MCP",
            "description": "MCP Server 整合和工具調用功能",
        },
        {
            "name": "LLM",
            "description": "Ollama 本地 LLM 推理與嵌入",
        },
        {
            "name": "Chat",
            "description": "產品級 Chat 入口（Auto/收藏/手動模型選擇）",
        },
        {
            "name": "CrewAI",
            "description": "CrewAI 多角色協作引擎管理",
        },
        {
            "name": "File Upload",
            "description": "文件上傳和管理功能",
        },
        {
            "name": "Chunk Processing",
            "description": "文件分塊處理功能",
        },
        {
            "name": "File Metadata",
            "description": "文件元數據管理功能",
        },
        {
            "name": "NER",
            "description": "命名實體識別功能",
        },
        {
            "name": "RE",
            "description": "關係抽取功能",
        },
        {
            "name": "RT",
            "description": "關係類型分類功能",
        },
        {
            "name": "Triple Extraction",
            "description": "三元組提取功能",
        },
        {
            "name": "Knowledge Graph Builder",
            "description": "知識圖譜構建功能",
        },
        {
            "name": "Knowledge Graph Query",
            "description": "知識圖譜查詢功能",
        },
        {
            "name": "Workflows",
            "description": "工作流執行功能（LangChain、AutoGen、混合模式）",
        },
    ],
)

# OAuth2 和監控代理路由
if oauth2_router:
    app.include_router(oauth2_router.router, prefix=API_PREFIX, tags=["OAuth2 SSO"])
    logger.info("OAuth2 SSO router registered")

if monitoring_proxy_router:
    app.include_router(monitoring_proxy_router.router, tags=["Monitoring Proxy"])
    logger.info("Monitoring proxy router registered")

# 添加中間件（順序很重要：Request ID -> Security -> Logging -> Error Handler -> CORS）
app.add_middleware(RequestIDMiddleware)

# 條件性添加安全中間件（僅當 SECURITY_ENABLED=true 時啟用）
security_settings = get_security_settings()
if security_settings.enabled:
    app.add_middleware(SecurityMiddleware)
    logger.info("Security middleware enabled")

app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# WBS-2.4: 監控與日誌 - Prometheus 指標中間件（在所有中間件之前，以便收集所有請求）
if PROMETHEUS_AVAILABLE:
    app.add_middleware(PrometheusMiddleware, app_name="ai-box-api")

# 配置 CORS（最後添加，確保在所有中間件之後）
# 注意：文件上傳需要支持 multipart/form-data，這已經通過 allow_headers=["*"] 支持
# 允許的來源：支持本地開發和生產環境
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
if cors_origins_env == "*":
    allow_origins = ["*"]
else:
    allow_origins = [origin.strip() for origin in cors_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],  # 包括 POST（用於文件上傳）
    allow_headers=["*"],  # 包括 Content-Type（multipart/form-data）
    expose_headers=["*"],  # 暴露所有響應頭，包括自定義頭
)


# 添加 RequestValidationError 異常處理器（在路由之前）
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """處理請求驗證錯誤，輸出詳細的錯誤信息"""
    error_details = exc.errors()

    # 嘗試讀取請求體
    try:
        body = await request.body()
        body_str = body.decode("utf-8")[:1000] if body else None
    except Exception:
        body_str = None

    # 使用 print 確保錯誤信息一定會輸出（输出到 stdout，uvicorn 会捕获）
    error_summary = f"""
{"=" * 80}
❌ RequestValidationError: {request.method} {request.url.path}
{"=" * 80}
Request body preview: {body_str}
Validation errors ({len(error_details)}):"""

    for i, error in enumerate(error_details, 1):
        error_summary += f"""
  {i}. Location: {error.get("loc")}
     Type: {error.get("type")}
     Message: {error.get("msg")}
     Input: {error.get("input")}"""

    error_summary += f"\n{'=' * 80}\n"

    print(error_summary)

    # 記錄到日誌（使用 logger.error 确保写入日志文件）
    logger.error(
        f"Request validation error: path={request.url.path}, method={request.method}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "errors": error_details,
            "body_preview": body_str,
        },
    )

    # 也使用 logger.error 记录每个错误详情
    for i, error in enumerate(error_details, 1):
        logger.error(
            f"Validation error {i}: loc={error.get('loc')}, type={error.get('type')}, msg={error.get('msg')}, input={error.get('input')}"
        )

    # 修改時間：2026-01-28 - 檢查是否是空查詢錯誤，返回友好錯誤消息
    # 檢查是否是 chat 端點的空查詢錯誤
    if request.url.path.endswith("/chat") and request.method == "POST":
        # 添加調試日誌
        logger.debug(
            f"Checking empty query in exception handler: path={request.url.path}, "
            f"method={request.method}, error_count={len(error_details)}"
        )

        # 檢查是否是 content 字段的 min_length 錯誤
        is_empty_query = False
        for error in error_details:
            error_loc = error.get("loc", [])
            error_type = error.get("type", "")
            error_msg = error.get("msg", "")

            # 添加調試日誌
            logger.debug(
                f"Error check in exception handler: loc={error_loc}, type={error_type}, "
                f"msg={error_msg}, loc_length={len(error_loc)}"
            )

            # 檢查是否是 messages[].content 的 min_length 錯誤
            # error_loc 格式: ("body", "messages", 0, "content") 或 ["body", "messages", 0, "content"]
            # 修改時間：2026-01-28 - 支持所有可能的錯誤類型和位置格式
            error_loc_list = list(error_loc) if not isinstance(error_loc, list) else error_loc

            if (
                len(error_loc_list) >= 4
                and error_loc_list[0] == "body"
                and error_loc_list[1] == "messages"
                and isinstance(error_loc_list[2], int)
                and error_loc_list[3] == "content"
                and (
                    "min_length" in error_type
                    or "string_too_short" in error_type
                    or "value_error" in error_type
                    or "string_type" in error_type
                    or "greater_than_equal" in error_type
                    or "less_than_equal" in error_type
                    or ("string" in error_type and "length" in error_msg.lower())
                )
            ):
                is_empty_query = True
                logger.info(
                    f"Empty query detected in exception handler: error_type={error_type}, "
                    f"error_loc={error_loc}, error_msg={error_msg}"
                )
                break

        if is_empty_query:
            # 使用 KA-Agent 的錯誤處理器生成友好錯誤消息
            try:
                from agents.builtin.ka_agent.error_handler import KAAgentErrorHandler

                error_feedback = KAAgentErrorHandler.missing_parameter(
                    parameter_name="instruction",
                    context="用戶查詢為空",
                )

                # 返回友好錯誤消息（使用 400 而非 422）
                from api.core.response import APIResponse

                logger.info(
                    f"Returning friendly empty query error: error_type={error_feedback.error_type.value}, "
                    f"user_message={error_feedback.user_message[:100]}"
                )

                return APIResponse.error(
                    message=error_feedback.user_message,
                    error_code="MISSING_PARAMETER",
                    details={
                        "error_type": error_feedback.error_type.value,
                        "suggested_action": error_feedback.suggested_action.value,
                        "clarifying_questions": error_feedback.clarifying_questions,
                    },
                    status_code=400,
                )
            except Exception as e:
                logger.warning(f"Failed to generate KA-Agent error feedback: {e}", exc_info=True)

    # 返回標準錯誤響應
    from api.core.response import APIResponse

    return APIResponse.error(
        message="Request validation failed",
        error_code="VALIDATION_ERROR",
        details={"errors": error_details},
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


# 註冊路由
app.include_router(health.router, tags=["Health"])

# WBS-2.4: 監控與日誌 - Prometheus Metrics 端點
try:
    from api.routers import metrics

    app.include_router(metrics.router, tags=["Monitoring"])
    logger.info("Prometheus Metrics 路由已註冊")
except ImportError:
    logger.warning("Prometheus Metrics 路由未註冊（模組不可用）")

app.include_router(auth.router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(data_consent.router, prefix=API_PREFIX, tags=["Data Consent"])
app.include_router(audit_log.router, prefix=API_PREFIX, tags=["Audit Logs"])
app.include_router(system_admin.router, prefix=API_PREFIX, tags=["System Admin"])
app.include_router(service_monitor.router, prefix=API_PREFIX, tags=["Service Monitor"])
app.include_router(service_alert.router, prefix=API_PREFIX, tags=["Service Alert"])
app.include_router(alert_webhook.router, prefix=API_PREFIX, tags=["Alert Webhook"])
app.include_router(prometheus_compat.router, prefix=API_PREFIX, tags=["Prometheus Compat"])
app.include_router(security_group.router, prefix=API_PREFIX, tags=["Security Group"])
app.include_router(system_config.router, prefix=API_PREFIX, tags=["System Config"])
app.include_router(user_account.router, prefix=API_PREFIX, tags=["User Account"])
app.include_router(user_sessions.router, prefix=API_PREFIX, tags=["User Session"])
app.include_router(user_tasks.router, prefix=API_PREFIX, tags=["User Tasks"])


# 添加版本信息端點
@app.get("/version", tags=["Health"])
async def get_version():
    """
    獲取 API 版本信息

    Returns:
        API 版本信息
    """
    return JSONResponse(content=get_version_info())


# 註冊版本化路由
app.include_router(agents.router, prefix=API_PREFIX, tags=["Agents"])
app.include_router(agent_registry.router, prefix=API_PREFIX, tags=["Agent Registry"])
app.include_router(agent_catalog.router, prefix=API_PREFIX, tags=["Agent Catalog"])
app.include_router(agent_category.router, prefix=API_PREFIX, tags=["Agent Categories"])
app.include_router(agent_display_config.router, prefix=API_PREFIX, tags=["Agent Display Config"])
app.include_router(agent_auth.router, prefix=API_PREFIX, tags=["Agent Authentication"])

# OAuth2 SSO 路由
if oauth2_router:
    app.include_router(oauth2_router.router, prefix=API_PREFIX, tags=["OAuth2 SSO"])
    logger.info("OAuth2 SSO router registered")

# 監控代理路由
if monitoring_proxy_router:
    app.include_router(monitoring_proxy_router.router, prefix=API_PREFIX, tags=["Monitoring Proxy"])
    logger.info("Monitoring proxy router registered")
app.include_router(agent_secret.router, prefix=API_PREFIX, tags=["Agent Secret"])
app.include_router(task_analyzer.router, prefix=API_PREFIX, tags=["Task Analyzer"])
# Agent 註冊申請路由（公開路由 + 管理員路由）
app.include_router(agent_registration.public_router, prefix=API_PREFIX, tags=["Agent Registration"])
app.include_router(
    agent_registration.admin_router, prefix=API_PREFIX, tags=["Agent Request Management"]
)
app.include_router(orchestrator.router, prefix=API_PREFIX, tags=["Agent Orchestrator"])
app.include_router(planning.router, prefix=API_PREFIX, tags=["Planning Agent"])
app.include_router(execution.router, prefix=API_PREFIX, tags=["Execution Agent"])
app.include_router(review.router, prefix=API_PREFIX, tags=["Review Agent"])
app.include_router(mcp.router, prefix=API_PREFIX, tags=["MCP"])
# ChromaDB router 已移除（已迁移到 Qdrant）

# 監控代理路由
if monitoring_proxy_router:
    app.include_router(monitoring_proxy_router.router, prefix=API_PREFIX, tags=["Monitoring Proxy"])
    logger.info("Monitoring proxy router registered")
app.include_router(file_metadata.router, prefix=API_PREFIX, tags=["File Metadata"])
app.include_router(file_management.router, prefix=API_PREFIX, tags=["File Management"])
app.include_router(file_upload.router, prefix=API_PREFIX, tags=["File Upload"])
app.include_router(agent_files.router, prefix=API_PREFIX, tags=["Agent Files"])
app.include_router(reports.router, prefix=API_PREFIX, tags=["Reports"])
app.include_router(chat.router, prefix=API_PREFIX, tags=["Chat"])
app.include_router(chat_module.router, prefix="/api/v2", tags=["Chat V2"])
app.include_router(config_definitions.router, prefix=API_PREFIX, tags=["Config Definitions"])
app.include_router(ontology.router, prefix=API_PREFIX)
# app.include_router(knowledge_ontology.router, prefix=API_PREFIX, tags=["Knowledge Ontology"])  # 註釋掉：檔案位置錯誤
app.include_router(llm_models.router, prefix=API_PREFIX, tags=["LLM Models"])
app.include_router(moe.router, prefix=API_PREFIX, tags=["MoE"])
app.include_router(moe_metrics.router, prefix=API_PREFIX, tags=["MoE Metrics"])
app.include_router(agent_status.router, prefix=API_PREFIX, tags=["Agent Status"])
app.include_router(rq_monitor.router, prefix=API_PREFIX, tags=["RQ Monitor"])


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info(f"AI Box API Gateway starting up... Version: {version_info['version']}")

    # 初始化配置元數據系統（Phase 10: ConfigMetadata）
    try:
        from services.api.core.config import initialize_config_system

        initialize_config_system()
    except Exception as e:
        logger.error(f"Failed to initialize config metadata system: {e}")

    # 初始化並註冊內建 Agent（需要註冊到 Registry 以便 Agent Discovery 發現）
    try:
        from agents.builtin import initialize_builtin_agents, register_builtin_agents

        # 先初始化內建 Agent
        builtin_agents = initialize_builtin_agents()
        logger.info(
            f"Initialized {len(builtin_agents)} builtin agents: {list(builtin_agents.keys())}"
        )

        # 註冊內建 Agent 到 Registry（特別是 document-editing-agent）
        registered_agents = register_builtin_agents()
        logger.info(
            f"Registered {len(registered_agents)} builtin agents to registry: {list(registered_agents.keys())}"
        )
    except Exception as e:
        # SeaweedFS 連接失敗是預期的（服務可能未運行），使用 WARNING 而不是 ERROR
        error_msg = str(e)
        if (
            "SeaweedFS" in error_msg
            or "localhost:8333" in error_msg
            or "Connection was closed" in error_msg
        ):
            logger.warning(
                f"Failed to initialize/register builtin agents (SeaweedFS not available, this is expected if service is not running): {e}"
            )
        else:
            logger.error(f"Failed to initialize/register builtin agents: {e}")

    # 註冊核心 Agent（註冊為內部 Agent）
    try:
        from agents.core import register_core_agents

        core_agents = register_core_agents()
        logger.info(f"Registered {len(core_agents)} core agents: {list(core_agents.keys())}")
    except Exception as e:
        logger.error(f"Failed to register core agents: {e}")

    # 初始化 LLM 模型數據（如果數據庫為空）
    try:
        from services.api.services.llm_model_service import get_llm_model_service

        service = get_llm_model_service()
        # 檢查數據庫中是否有模型
        existing_models = service.get_all(None)
        if len(existing_models) == 0:
            logger.info("數據庫中沒有模型數據，開始自動遷移...")
            # 執行遷移（同步函數，在異步上下文中運行）
            import asyncio

            from services.api.services.migrations.migrate_llm_models import migrate

            await asyncio.to_thread(migrate)
            logger.info("LLM 模型數據遷移完成")
        else:
            logger.info(f"數據庫中已有 {len(existing_models)} 個模型，跳過遷移")
    except Exception as e:
        logger.warning(f"LLM 模型數據遷移失敗（不影響啟動）: {e}")

    # 啟動 Agent 健康監控（可選，根據配置啟用）
    try:
        from agents.services.registry.health_monitor import AgentHealthMonitor
        from agents.services.registry.registry import get_agent_registry

        registry = get_agent_registry()
        health_monitor = AgentHealthMonitor(
            registry=registry,
            check_interval=int(os.getenv("AGENT_HEALTH_CHECK_INTERVAL", "60")),
            heartbeat_timeout=int(os.getenv("AGENT_HEARTBEAT_TIMEOUT", "300")),
        )
        await health_monitor.start()
        logger.info("Agent health monitor started")
    except Exception as e:
        logger.warning(f"Failed to start agent health monitor: {e}")

    # 初始化系統配置（從默認配置加載到 ArangoDB）
    try:
        from services.api.services.config_initializer import initialize_system_configs

        init_results = initialize_system_configs(force=False)
        initialized_count = sum(1 for success in init_results.values() if success)
        skipped_count = len(init_results) - initialized_count
        logger.info(
            f"系統配置初始化完成: {initialized_count} 個已初始化，{skipped_count} 個已存在（跳過）"
        )
    except Exception as e:
        logger.warning(f"系統配置初始化失敗（不影響啟動）: {e}")

    # 初始化 MCP 第三方服務配置（從 .env 加載到 ArangoDB）
    try:
        from services.api.services.config_initializer import initialize_mcp_external_services_config

        mcp_config_initialized = initialize_mcp_external_services_config(force=False)
        if mcp_config_initialized:
            logger.info("MCP 第三方服務配置已初始化（從 .env 文件）")
        else:
            logger.debug("MCP 第三方服務配置已存在，跳過初始化")
    except Exception as e:
        logger.warning(f"MCP 第三方服務配置初始化失敗（不影響啟動）: {e}")

    # 初始化時間服務（單例模式，無需後台任務）
    try:
        from tools.time.smart_time_service import get_time_service

        get_time_service()  # 初始化單例
        logger.info("Time service initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize time service: {e}")

    # 初始化配置元數據系統（DefinitionLoader）
    try:
        from services.api.core.config import initialize_config_system

        initialize_config_system()
        logger.info("Config metadata system initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize config metadata system: {e}")

    # 啟動系統資源指標收集後台任務（Prometheus 監控）
    if PROMETHEUS_AVAILABLE:
        try:
            from services.api.middleware.prometheus import start_system_metrics_task

            start_system_metrics_task()
            logger.info("System metrics collection task started")
        except Exception as e:
            logger.warning(f"Failed to start system metrics task: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("AI Box API Gateway shutting down...")

    # 停止 Agent 健康監控
    try:
        # 注意：這裡需要保存全局的 health_monitor 實例引用才能停止
        # 暫時記錄日誌，實際實現需要保存實例引用
        logger.info("Stopping agent health monitor...")
    except Exception as e:
        logger.warning(f"Failed to stop agent health monitor: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host=os.getenv("API_GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("API_GATEWAY_PORT", "8000")),
        reload=os.getenv("ENV", "development") == "development",
    )
