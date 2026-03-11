
"""Data-Agent 服務入口

包含：
- 原 Data-Agent API
- Data-Agent-JP API (Schema Driven Query)
"""

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 載入環境變數（優先 data_agent/.env，備用 datalake-system/.env）
# 確保透過 uvicorn --reload 啟動時也能讀取 S3/LLM 等配置
_this_dir = Path(__file__).resolve().parent
_agent_env = _this_dir / ".env"
_root_env = _this_dir.parent / ".env"
if _agent_env.exists():
    load_dotenv(dotenv_path=_agent_env, override=False)
elif _root_env.exists():
    load_dotenv(dotenv_path=_root_env, override=False)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Data-Agent API",
    description="Data-Agent Service with Schema Driven Query Support",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
