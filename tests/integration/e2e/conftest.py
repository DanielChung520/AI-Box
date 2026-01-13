# 代碼功能說明: E2E 測試配置和 Fixtures
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""E2E 測試配置和共用 Fixtures"""

import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional
from unittest.mock import AsyncMock, Mock

import pytest
from dotenv import load_dotenv

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import SemanticUnderstandingOutput
from database.arangodb import ArangoDBClient

# 加載環境變數
base_dir = Path(__file__).resolve().parent.parent.parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)


@pytest.fixture(scope="session")
def test_env() -> dict:
    """測試環境配置"""
    return {
        "ARANGO_HOST": os.getenv("ARANGO_HOST", "http://localhost:8529"),
        "ARANGO_USER": os.getenv("ARANGO_USER", "root"),
        "ARANGO_PASSWORD": os.getenv("ARANGO_PASSWORD", ""),
        "ARANGO_DB": os.getenv("ARANGO_DB", "ai_box_test"),
        "CHROMA_HOST": os.getenv("CHROMA_HOST", "http://localhost:8000"),
    }


@pytest.fixture(scope="session")
def arangodb_client(test_env: dict) -> Generator[Optional[ArangoDBClient], None, None]:
    """創建 ArangoDB 客戶端（真實連接）"""
    try:
        client = ArangoDBClient(
            host=test_env["ARANGO_HOST"],
            username=test_env["ARANGO_USER"],
            password=test_env["ARANGO_PASSWORD"],
            database=test_env["ARANGO_DB"],
        )
        client.connect()
        yield client
        # 清理：關閉連接
        if client.db:
            client.close()
    except Exception as e:
        pytest.skip(f"ArangoDB 連接失敗: {e}")


@pytest.fixture
def task_analyzer() -> TaskAnalyzer:
    """創建 TaskAnalyzer 實例"""
    return TaskAnalyzer()


@pytest.fixture
def orchestrator() -> AgentOrchestrator:
    """創建 AgentOrchestrator 實例"""
    return AgentOrchestrator()


@pytest.fixture
def sample_task_request() -> dict:
    """示例任務請求"""
    return {
        "task": "查詢系統配置",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
        "session_id": "test_session_123",
    }


@pytest.fixture
def sample_simple_query() -> dict:
    """簡單查詢任務"""
    return {
        "task": "現在幾點？",
        "context": {"user_id": "test_user_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_config_task() -> dict:
    """配置操作任務"""
    return {
        "task": "查詢 GenAI 租戶策略配置",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_log_query_task() -> dict:
    """日誌查詢任務"""
    return {
        "task": "查詢審計日誌",
        "context": {"user_id": "test_user_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_complex_task() -> dict:
    """複雜多步驟任務"""
    return {
        "task": "分析用戶數據並生成報告，然後發送郵件通知",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_high_risk_task() -> dict:
    """高風險任務（觸發風險檢查）"""
    return {
        "task": "刪除所有用戶數據並清空數據庫",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def mock_llm_response() -> dict:
    """模擬 LLM 響應"""
    return {
        "topics": ["系統配置", "GenAI"],
        "entities": ["tenant_policy"],
        "action_signals": ["query", "read"],
        "modality": "text",
        "intent_type": "query",
        "needs_tools": False,
        "needs_agent": False,
    }


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """自動清理測試數據（每個測試後執行）"""
    yield
    # 這裡可以添加清理邏輯，例如刪除測試創建的數據
    pass


# ==================== v4.0 測試 Fixtures ====================

@pytest.fixture
def mock_router_llm():
    """模擬 Router LLM 服務"""
    mock = AsyncMock()
    mock.route_v4 = AsyncMock(
        return_value=SemanticUnderstandingOutput(
            topics=["document", "system_design"],
            entities=["Document Editing Agent"],
            action_signals=["design"],
            modality="instruction",
            certainty=0.92,
        )
    )
    return mock


@pytest.fixture
def mock_orchestrator():
    """模擬 Agent Orchestrator 服務"""
    mock = AsyncMock(spec=AgentOrchestrator)
    mock.execute_task = AsyncMock(
        return_value={
            "success": True,
            "result": {"status": "completed", "output": "Task executed successfully"},
            "agent_id": "document-editing-agent",
            "execution_time_ms": 150,
        }
    )
    return mock


@pytest.fixture
def mock_security_agent_denied():
    """模擬 Security Agent 權限檢查 - 拒絕"""
    mock = AsyncMock()
    mock.check_permission = AsyncMock(
        return_value={
            "allowed": False,
            "requires_confirmation": False,
            "risk_level": "high",
            "reasons": ["User does not have permission to perform this action"],
        }
    )
    return mock


@pytest.fixture
def sample_document_editing_task() -> Dict[str, Any]:
    """文檔編輯任務"""
    return {
        "task": "在 API 規格文檔中添加新的端點定義",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
        "session_id": "test_session_123",
    }


@pytest.fixture
def sample_general_query_task() -> Dict[str, Any]:
    """通用查詢任務（Fallback Intent）"""
    return {
        "task": "什麼是 AI-Box？",
        "context": {"user_id": "test_user_123"},
        "user_id": "test_user_123",
    }
