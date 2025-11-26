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

from services.api.middleware.request_id import RequestIDMiddleware
from services.api.middleware.logging import LoggingMiddleware
from services.api.middleware.error_handler import ErrorHandlerMiddleware
from services.api.routers import (
    health,
    agents,
    task_analyzer,
    orchestrator,
    mcp,
    chromadb,
    llm,
)
from services.api.core.version import get_version_info, API_PREFIX
from services.security.config import get_security_settings
from services.security.middleware import SecurityMiddleware

# 配置日誌
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

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
app.include_router(task_analyzer.router, prefix=API_PREFIX, tags=["Task Analyzer"])
app.include_router(orchestrator.router, prefix=API_PREFIX, tags=["Agent Orchestrator"])
app.include_router(mcp.router, prefix=API_PREFIX, tags=["MCP"])
app.include_router(chromadb.router, prefix=API_PREFIX, tags=["ChromaDB"])
app.include_router(llm.router, prefix=API_PREFIX, tags=["LLM"])


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info(f"AI Box API Gateway starting up... Version: {version_info['version']}")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("AI Box API Gateway shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "services.api.main:app",
        host=os.getenv("API_GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("API_GATEWAY_PORT", "8000")),
        reload=os.getenv("ENV", "development") == "development",
    )
