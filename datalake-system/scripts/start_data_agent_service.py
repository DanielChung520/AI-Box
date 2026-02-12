# 代碼功能說明: Data Agent 服務啟動腳本（Datalake System 獨立版本）
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Data Agent 獨立服務啟動腳本

使用 FastAPI 和 uvicorn 啟動 Data Agent HTTP 服務，提供 AgentServiceProtocol 接口。
"""

import os
import sys
from pathlib import Path

ORACLE_LIB_PATH = os.getenv("ORACLE_LIB_PATH", "/home/daniel/instantclient_23_26")
if ORACLE_LIB_PATH and os.path.exists(ORACLE_LIB_PATH):
    os.environ["LD_LIBRARY_PATH"] = f"{ORACLE_LIB_PATH}:{os.environ.get('LD_LIBRARY_PATH', '')}"
    print(f"✅ Oracle Client library path 設定完成: {ORACLE_LIB_PATH}")
else:
    print(f"⚠️ Oracle Client library not found at: {ORACLE_LIB_PATH}")

# 獲取 datalake-system 目錄
DATALAKE_SYSTEM_DIR = Path(__file__).resolve().parent.parent
# 獲取 AI-Box 根目錄
AI_BOX_ROOT = DATALAKE_SYSTEM_DIR.parent

# 添加 AI-Box 根目錄到 Python 路徑
sys.path.insert(0, str(AI_BOX_ROOT))

# 添加 datalake-system 到 Python 路徑
sys.path.insert(0, str(DATALAKE_SYSTEM_DIR))

from dotenv import load_dotenv

# 加載環境變數（使用 data_agent 專屬配置）
# 優先加載 data_agent/.env，如果不存在則使用 AI-Box/.env
agent_env_path = DATALAKE_SYSTEM_DIR / "data_agent" / ".env"
box_env_path = AI_BOX_ROOT / ".env"

if agent_env_path.exists():
    env_path = agent_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"✅ 已加載 Data-Agent 專屬環境配置: {env_path}")
else:
    env_path = box_env_path
    load_dotenv(dotenv_path=env_path)
    print(f"⚠️ Data-Agent 專屬配置不存在，使用 AI-Box 配置: {env_path}")

# 清除 Ollama 設定的緩存，確保環境變數生效
try:
    from api.core.settings import get_ollama_settings

    get_ollama_settings.cache_clear()
    print("✅ 已清除 Ollama 設定緩存")
except Exception as e:
    print(f"⚠️ 清除 Ollama 設定緩存失敗: {e}")

import sys
from pathlib import Path

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = Path(__file__).resolve().parent.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))

import uvicorn
from data_agent.agent import DataAgent
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from agents.services.protocol.base import AgentServiceRequest, AgentServiceResponse
from fastapi.middleware.cors import CORSMiddleware

# 創建 FastAPI 應用
app = FastAPI(
    title="Data Agent Service (Datalake System)",
    description="Data Agent 獨立服務，提供數據查詢、數據字典管理和 Schema 管理功能",
    version="1.0.0",
)

# CORS 配置
from starlette.middleware.cors import CORSMiddleware as StarletteCORSMiddleware

app.add_middleware(
    StarletteCORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# Schema RAG 配置路徑
schema_config_path = str(DATALAKE_SYSTEM_DIR / "metadata" / "config" / "schema_rag_config.yaml")

# 初始化 Data Agent（使用新版 TextToSQLServiceWithRAG）
data_agent = DataAgent(
    text_to_sql_service=None,  # 使用預設的 TextToSQLServiceWithRAG
)


@app.post("/execute", response_model=AgentServiceResponse)
async def execute(request: AgentServiceRequest) -> AgentServiceResponse:
    """執行數據查詢任務

    AgentServiceProtocol HTTP 接口實現
    """
    try:
        result = await data_agent.execute(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health() -> dict:
    """健康檢查端點"""
    try:
        status = await data_agent.health_check()
        return {
            "status": status.value,
            "service": "data_agent",
            "system": "datalake-system",
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "service": "data_agent",
                "system": "datalake-system",
                "error": str(e),
            },
        )


@app.get("/capabilities")
async def capabilities() -> dict:
    """獲取服務能力端點"""
    try:
        caps = await data_agent.get_capabilities()
        return caps
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/text-to-sql")
async def text_to_sql(request: dict) -> dict:
    """直接從自然語言生成 SQL

    簡化的 Text-to-SQL 接口：
    1. 接收自然語言
    2. AI 直接理解生成 SQL
    3. 執行 SQL 返回結果
    """
    try:
        instruction = request.get("instruction", "")
        if not instruction:
            return {"success": False, "error": "需要提供 instruction 參數"}

        # 生成 SQL
        sql_result = await data_agent._text_to_sql_service.generate_sql(instruction)

        if not sql_result["success"]:
            return sql_result

        # 執行 SQL
        exec_result = await data_agent._handle_execute_sql_direct(sql_result["sql"])

        return {
            "success": True,
            "sql": sql_result["sql"],
            "result": exec_result.get("result", {}),
        }

    except Exception as e:
        logger.error(f"Text-to-SQL 失敗: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


# =============================================================================
# Data-Agent-JP (Schema Driven Query) 路由
# =============================================================================
try:
    from data_agent.services.schema_driven_query.parser import SimpleNLQParser
    from data_agent.services.schema_driven_query.models import (
        ExecuteRequest,
        ExecuteResponse,
        HealthResponse,
        QueryResult,
    )
    from data_agent.services.schema_driven_query.resolver import Resolver
    from data_agent.services.schema_driven_query.loaders import get_schema_loader

    _resolver_instance = None

    def get_resolver() -> Resolver:
        global _resolver_instance
        if _resolver_instance is None:
            from data_agent.services.schema_driven_query.config import get_config

            config = get_config()
            loader = get_schema_loader(config)
            resolver = Resolver(
                config=config,
                intents=loader.load_intents(),
                concepts=loader.load_concepts(),
                bindings=loader.load_bindings(),
            )
            _resolver_instance = resolver
        return _resolver_instance

    @app.post("/jp/execute")
    async def jp_execute(request: ExecuteRequest) -> ExecuteResponse:
        """Data-Agent-JP Schema Driven Query 執行"""

        try:
            resolver = get_resolver()
            result = resolver.resolve(request.task_data.nlq)

            if result["status"] == "error":
                return ExecuteResponse(
                    status="error",
                    task_id=request.task_id,
                    error_code=result.get("error_code", "UNKNOWN_ERROR"),
                    message=result.get("message", "Unknown error"),
                )

            sql = result["sql"]

            from data_agent.services.schema_driven_query.executor import ExecutorFactory
            from data_agent.services.schema_driven_query.config import get_config

            config = get_config()
            # 強制使用 DUCKDB
            config.datasource = "DUCKDB"

            factory = ExecutorFactory(config=config)
            executor = factory.get_executor()

            # 添加超時控制
            timeout = (
                request.task_data.options.timeout
                if hasattr(request.task_data, "options") and request.task_data.options
                else 30
            )
            exec_result = executor.execute(sql, timeout=timeout)

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
                status="error", task_id=request.task_id, error_code="INTERNAL_ERROR", message=str(e)
            )

    @app.get("/jp/health", response_model=HealthResponse)
    async def jp_health() -> HealthResponse:
        """Data-Agent-JP 健康檢查"""
        return HealthResponse(status="healthy", service="data-agent-jp", version="1.0.0")

    print("✅ Data-Agent-JP (Schema Driven Query) 路由已載入")

except ImportError as e:
    import traceback

    traceback.print_exc()
    print(f"⚠️ Data-Agent-JP 路由載入失敗: {e}")
    """主函數：啟動服務"""
    # 從環境變數讀取配置
    host = os.getenv("DATA_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("DATA_AGENT_SERVICE_PORT", "8004"))

    print(f"Starting Data Agent Service (Datalake System) on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Capabilities: http://{host}:{port}/capabilities")
    print(f"Execute endpoint: http://{host}:{port}/execute")


def main() -> None:
    """主函數：啟動服務"""
    # 從環境變數讀取配置
    host = os.getenv("DATA_AGENT_SERVICE_HOST", "localhost")
    port = int(os.getenv("DATA_AGENT_SERVICE_PORT", "8004"))

    print(f"Starting Data Agent Service (Datalake System) on {host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    print(f"Capabilities: http://{host}:{port}/capabilities")
    print(f"Execute endpoint: http://{host}:{port}/execute")

    # 啟動服務
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
