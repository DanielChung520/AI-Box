# 代碼功能說明: FastAPI 應用主入口
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""FastAPI 應用主入口文件"""

import os
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
    file_upload,
    chunk_processing,
    file_metadata,
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
)

from api.core.version import get_version_info, API_PREFIX
from system.security.config import get_security_settings
from system.security.middleware import SecurityMiddleware

# 配置日誌
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(health.router, tags=["Health"])


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
app.include_router(task_analyzer.router, prefix=API_PREFIX, tags=["Task Analyzer"])
app.include_router(orchestrator.router, prefix=API_PREFIX, tags=["Agent Orchestrator"])
app.include_router(planning.router, prefix=API_PREFIX, tags=["Planning Agent"])
app.include_router(execution.router, prefix=API_PREFIX, tags=["Execution Agent"])
app.include_router(review.router, prefix=API_PREFIX, tags=["Review Agent"])
app.include_router(mcp.router, prefix=API_PREFIX, tags=["MCP"])
app.include_router(chromadb.router, prefix=API_PREFIX, tags=["ChromaDB"])
app.include_router(llm.router, prefix=API_PREFIX, tags=["LLM"])
# 條件性註冊 CrewAI 路由
if CREWAI_AVAILABLE and crewai is not None and crewai_tasks is not None:
    app.include_router(crewai.router, prefix=API_PREFIX, tags=["CrewAI"])
    app.include_router(crewai_tasks.router, prefix=API_PREFIX, tags=["CrewAI"])
    logger.info("CrewAI 路由已註冊")
else:
    logger.warning("CrewAI 路由未註冊（模組不可用）")
app.include_router(file_upload.router, prefix=API_PREFIX, tags=["File Upload"])
app.include_router(
    chunk_processing.router, prefix=API_PREFIX, tags=["Chunk Processing"]
)
app.include_router(file_metadata.router, prefix=API_PREFIX, tags=["File Metadata"])
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
