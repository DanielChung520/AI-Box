# Data-Agent 主入口
# 代碼功能說明: Data-Agent 服務入口
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Data-Agent 服務入口

包含：
- 原 Data-Agent API
- Data-Agent-JP API (Schema Driven Query)
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 設定日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 建立 FastAPI 應用
app = FastAPI(
    title="Data-Agent API",
    description="Data-Agent Service with Schema Driven Query Support",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 路由註冊
def register_routers():
    """註冊所有路由"""

    # 原 Data-Agent 路由
    try:
        from .routers.data_agent import router as data_agent_router

        app.include_router(data_agent_router, prefix="/api/v1/data-agent")
        logger.info("Registered data_agent router")
    except ImportError as e:
        logger.warning(f"Could not register data_agent router: {e}")

    # Data-Agent-JP 路由 (Schema Driven Query)
    try:
        from .routers.data_agent_jp import router as data_agent_jp_router

        app.include_router(data_agent_jp_router, prefix="/api/v1/data-agent")
        logger.info("Registered data_agent_jp router")
    except ImportError as e:
        logger.warning(f"Could not register data_agent_jp router: {e}")


register_routers()


@app.get("/")
async def root():
    """根路徑"""
    return {
        "service": "Data-Agent API",
        "version": "1.0.0",
        "endpoints": {
            "data_agent": "/api/v1/data-agent/execute",
            "data_agent_jp": "/api/v1/data-agent/jp/execute",
            "health": "/api/v1/data-agent/jp/health",
        },
    }


@app.get("/health")
async def health():
    """健康檢查"""
    return {"status": "healthy", "service": "data-agent"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8004)
