# 代碼功能說明: FastAPI 應用主入口
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""FastAPI 應用主入口文件"""

import logging
import os

from api_gateway.middleware.error_handler import ErrorHandlerMiddleware
from api_gateway.middleware.logging import LoggingMiddleware
from api_gateway.routers import agents, health, orchestrator, task_analyzer
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 配置日誌
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="AI Box API Gateway",
    version="1.0.0",
    description="AI Box 統一 API 入口",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加自定義中間件
app.add_middleware(LoggingMiddleware)
app.add_middleware(ErrorHandlerMiddleware)

# 註冊路由
app.include_router(health.router, tags=["Health"])
app.include_router(agents.router, prefix="/api/v1", tags=["Agents"])
app.include_router(task_analyzer.router, prefix="/api/v1", tags=["Task Analyzer"])
app.include_router(orchestrator.router, prefix="/api/v1", tags=["Agent Orchestrator"])


@app.on_event("startup")
async def startup_event():
    """應用啟動事件"""
    logger.info("AI Box API Gateway starting up...")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉事件"""
    logger.info("AI Box API Gateway shutting down...")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api_gateway.main:app",
        host=os.getenv("API_GATEWAY_HOST", "0.0.0.0"),
        port=int(os.getenv("API_GATEWAY_PORT", "8000")),
        reload=os.getenv("ENV", "development") == "development",
    )
