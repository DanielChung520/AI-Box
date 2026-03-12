# 代碼功能說明: DT-Agent FastAPI 應用入口
# 創建日期: 2026-03-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-11

from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI

from dt_agent.src.api.routes import dt_router

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 應用生命週期管理"""
    logger.info("DT-Agent starting", port=8005)
    yield
    logger.info("DT-Agent shutting down")


app = FastAPI(
    title="DT-Agent",
    version="1.0.0",
    description="Schema-Driven Query Agent for Datalake System",
    lifespan=lifespan,
)

# 掛載 DT-Agent 路由
app.include_router(dt_router, prefix="/api/v1/dt-agent", tags=["dt-agent"])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
