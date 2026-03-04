# 代碼功能說明: Data-Agent-JP 獨立服務啟動腳本
# 創建日期: 2026-02-10
# 創建人: Daniel Chung

"""Data-Agent-JP 獨立服務啟動腳本

使用 FastAPI 和 uvicorn 啟動 Data-Agent-JP Schema Driven Query 服務。
不依賴舊的 DataAgent，專門用於 JP ERP 查詢。
"""

import os
import sys
from pathlib import Path

# 在任何其他導入之前設置 Oracle Client 環境變數
ORACLE_LIB_PATH = os.getenv("ORACLE_LIB_PATH", "/home/daniel/instantclient_23_26")
if ORACLE_LIB_PATH and os.path.exists(ORACLE_LIB_PATH):
    os.environ["LD_LIBRARY_PATH"] = f"{ORACLE_LIB_PATH}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    print(f"✅ Oracle Client library path: {ORACLE_LIB_PATH}")

# 獲取 datalake-system 目錄
DATALAKE_SYSTEM_DIR = Path(__file__).resolve().parent.parent
AI_BOX_ROOT = DATALAKE_SYSTEM_DIR.parent

# 添加路徑
sys.path.insert(0, str(DATALAKE_SYSTEM_DIR))
sys.path.insert(0, str(AI_BOX_ROOT))

from dotenv import load_dotenv

env_path = DATALAKE_SYSTEM_DIR / "data_agent" / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    print(f"✅ 已加載環境配置: {env_path}")

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from data_agent.services.schema_driven_query.parser import SimpleNLQParser
from data_agent.services.schema_driven_query.resolver import Resolver
from data_agent.services.schema_driven_query.loaders import get_schema_loader
from data_agent.services.schema_driven_query.models import (
    ExecuteRequest,
    ExecuteResponse,
    HealthResponse,
    QueryResult,
)
from data_agent.services.schema_driven_query.config import get_config

app = FastAPI(
    title="Data-Agent-JP Service",
    description="Data-Agent-JP Schema Driven Query Service for Japanese TiTop ERP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_resolver_instance = None


def get_resolver() -> Resolver:
    global _resolver_instance
    if _resolver_instance is None:
        config = get_config()
        loader = get_schema_loader(config)
        _resolver_instance = Resolver(
            config=config,
            intents=loader.load_intents(),
            concepts=loader.load_concepts(),
            bindings=loader.load_bindings(),
        )
        print("✅ Resolver 初始化完成")
    return _resolver_instance


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """健康檢查"""
    return HealthResponse(status="healthy", service="data-agent-jp", version="1.0.0")


@app.get("/jp/health", response_model=HealthResponse)
async def jp_health() -> HealthResponse:
    """Data-Agent-JP 健康檢查"""
    return HealthResponse(status="healthy", service="data-agent-jp", version="1.0.0")


@app.post("/jp/execute", response_model=ExecuteResponse)
async def jp_execute(request: ExecuteRequest) -> ExecuteResponse:
    """Data-Agent-JP Schema Driven Query 執行"""
    try:
        resolver = get_resolver()
        # 傳遞外部參數（如 inventory_location）
        result = resolver.resolve(request.task_data.nlq, params=request.task_data.params)

        if result["status"] == "error":
            return ExecuteResponse(
                status="error",
                task_id=request.task_id,
                error_code=result.get("error_code", "UNKNOWN_ERROR"),
                message=result.get("message", "Unknown error"),
            )

        sql = result["sql"]

        from data_agent.services.schema_driven_query.executor import SQLExecutor

        executor = SQLExecutor()
        exec_result = executor.execute(sql)

        query_result = QueryResult(
            sql=sql,
            data=exec_result.get("data", []),
            row_count=exec_result.get("row_count", 0),
            execution_time_ms=exec_result.get("execution_time_ms", 0),
        )

        return ExecuteResponse(
            status="success",
            task_id=request.task_id,
            result=query_result,
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return ExecuteResponse(
            status="error",
            task_id=request.task_id,
            error_code="INTERNAL_ERROR",
            message=str(e),
        )


def main():
    host = os.getenv("DATA_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("DATA_AGENT_SERVICE_PORT", "8004"))

    print(f"🚀 啟動 Data-Agent-JP Service on {host}:{port}")
    print(f"   Health: http://{host}:{port}/jp/health")
    print(f"   Execute: http://{host}:{port}/jp/execute")

    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
