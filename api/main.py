# 代碼功能說明: FastAPI 應用主入口
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-14 10:27:19 (UTC+8)
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from api.middleware.request_id import RequestIDMiddleware
from api.middleware.logging import LoggingMiddleware
from api.middleware.error_handler import ErrorHandlerMiddleware
from api.routers import (
    health,
    agents,
    task_analyzer,
    orchestrator,
    planning,
    execution,
    review,
    mcp,
    chromadb,
    llm,
    chat,
    docs_editing,
    genai_tenant_config,
    genai_user_config,
    file_upload,
    chunk_processing,
    file_metadata,
    file_management,
    data_quality,
    ner,
    re,
    rt,
    triple_extraction,
    kg_builder,
    kg_query,
    workflows,
    agent_registry,
    agent_catalog,
    agent_files,
    reports,
    auth,
    data_consent,
    audit_log,
    model_usage,
    user_tasks,
    rq_monitor,
)

# 可選導入 governance 路由
from types import ModuleType
from typing import Optional

governance: Optional[ModuleType] = None
try:
    from api.routers import governance  # type: ignore[no-redef]
except ImportError:
    pass
from api.routers import agent_auth
from api.routers import agent_secret

from api.core.version import get_version_info, API_PREFIX
from system.security.config import get_security_settings
from system.security.middleware import SecurityMiddleware

# 修改時間：2025-12-08 12:30:00 UTC+8 - 使用統一的日誌配置模組
from system.logging_config import setup_fastapi_logging

# 配置 FastAPI 日誌（使用 RotatingFileHandler，最大 500KB，保留 4 個備份）
setup_fastapi_logging()
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
            "name": "ChromaDB",
            "description": "ChromaDB 向量資料庫操作接口",
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

# 添加中間件（順序很重要：Request ID -> Security -> Logging -> Error Handler -> CORS）
app.add_middleware(RequestIDMiddleware)

# 條件性添加安全中間件（僅當 SECURITY_ENABLED=true 時啟用）
security_settings = get_security_settings()
if security_settings.enabled:
    app.add_middleware(SecurityMiddleware)
    logger.info("Security middleware enabled")

app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

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

# 註冊路由
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix=API_PREFIX, tags=["Authentication"])
app.include_router(data_consent.router, prefix=API_PREFIX, tags=["Data Consent"])
app.include_router(audit_log.router, prefix=API_PREFIX, tags=["Audit Logs"])


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
app.include_router(agent_auth.router, prefix=API_PREFIX, tags=["Agent Authentication"])
app.include_router(agent_secret.router, prefix=API_PREFIX, tags=["Agent Secret"])
app.include_router(task_analyzer.router, prefix=API_PREFIX, tags=["Task Analyzer"])
app.include_router(orchestrator.router, prefix=API_PREFIX, tags=["Agent Orchestrator"])
app.include_router(planning.router, prefix=API_PREFIX, tags=["Planning Agent"])
app.include_router(execution.router, prefix=API_PREFIX, tags=["Execution Agent"])
app.include_router(review.router, prefix=API_PREFIX, tags=["Review Agent"])
app.include_router(mcp.router, prefix=API_PREFIX, tags=["MCP"])
app.include_router(chromadb.router, prefix=API_PREFIX, tags=["ChromaDB"])
app.include_router(llm.router, prefix=API_PREFIX, tags=["LLM"])
# 修改時間：2025-12-13 17:28:02 (UTC+8) - 註冊產品級 Chat 入口
app.include_router(chat.router, prefix=API_PREFIX, tags=["Chat"])
app.include_router(docs_editing.router, prefix=API_PREFIX, tags=["Docs Editing"])
app.include_router(
    genai_tenant_config.router, prefix=API_PREFIX, tags=["GenAI Tenant Config"]
)
app.include_router(
    genai_user_config.router, prefix=API_PREFIX, tags=["GenAI User Config"]
)
# 條件性註冊 CrewAI 路由
if CREWAI_AVAILABLE and crewai is not None and crewai_tasks is not None:
    app.include_router(crewai.router, prefix=API_PREFIX, tags=["CrewAI"])
    app.include_router(crewai_tasks.router, prefix=API_PREFIX, tags=["CrewAI"])
    logger.info("CrewAI 路由已註冊")
else:
    logger.warning("CrewAI 路由未註冊（模組不可用）")
# 注意：file_management.router 必須在 file_upload.router 之前註冊
# 因為 file_management 包含 /tree 路由，需要優先匹配，避免被 file_upload 的 /{file_id} 路由匹配
app.include_router(file_management.router, prefix=API_PREFIX, tags=["File Management"])
app.include_router(user_tasks.router, prefix=API_PREFIX, tags=["User Tasks"])
app.include_router(file_upload.router, prefix=API_PREFIX, tags=["File Upload"])
app.include_router(rq_monitor.router, prefix=API_PREFIX, tags=["RQ Monitor"])
app.include_router(
    chunk_processing.router, prefix=API_PREFIX, tags=["Chunk Processing"]
)
app.include_router(file_metadata.router, prefix=API_PREFIX, tags=["File Metadata"])
app.include_router(model_usage.router, prefix=API_PREFIX, tags=["Model Usage"])
app.include_router(data_quality.router, prefix=API_PREFIX, tags=["Data Quality"])
if governance:
    app.include_router(governance.router, prefix=API_PREFIX, tags=["AI Governance"])
app.include_router(ner.router, prefix=API_PREFIX, tags=["NER"])
app.include_router(re.router, prefix=API_PREFIX, tags=["RE"])
app.include_router(rt.router, prefix=API_PREFIX, tags=["RT"])
app.include_router(
    triple_extraction.router, prefix=API_PREFIX, tags=["Triple Extraction"]
)
app.include_router(
    kg_builder.router, prefix=API_PREFIX, tags=["Knowledge Graph Builder"]
)
app.include_router(kg_query.router, prefix=API_PREFIX, tags=["Knowledge Graph Query"])
app.include_router(workflows.router, prefix=API_PREFIX, tags=["Workflows"])
app.include_router(agent_files.router, prefix=API_PREFIX, tags=["Agent Files"])
app.include_router(reports.router, prefix=API_PREFIX, tags=["Reports"])


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info(f"AI Box API Gateway starting up... Version: {version_info['version']}")

    # 初始化内建 Agent（无需注册到 Registry）
    try:
        from agents.builtin import initialize_builtin_agents

        builtin_agents = initialize_builtin_agents()
        logger.info(
            f"Initialized {len(builtin_agents)} builtin agents: {list(builtin_agents.keys())}"
        )
    except Exception as e:
        logger.error(f"Failed to initialize builtin agents: {e}")

    # 註冊核心 Agent（註冊為內部 Agent）
    try:
        from agents.core import register_core_agents

        core_agents = register_core_agents()
        logger.info(
            f"Registered {len(core_agents)} core agents: {list(core_agents.keys())}"
        )
    except Exception as e:
        logger.error(f"Failed to register core agents: {e}")

    # 啟動 Agent 健康監控（可選，根據配置啟用）
    try:
        from agents.services.registry.registry import get_agent_registry
        from agents.services.registry.health_monitor import AgentHealthMonitor

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
