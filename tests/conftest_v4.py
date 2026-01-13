# 代碼功能說明: v4.0 測試配置和 Fixtures - 階段七測試驗證準備工作
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""v4.0 測試配置和共用 Fixtures - 用於階段七測試驗證"""

import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from dotenv import load_dotenv

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import (
    SemanticUnderstandingOutput,
    TaskAnalysisRequest,
    TaskDAG,
    TaskNode,
)
from database.arangodb import ArangoDBClient

# 加載環境變數
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

# 測試環境配置
TEST_ARANGO_DB = os.getenv("ARANGO_DB_TEST", "ai_box_test")
TEST_CHROMA_COLLECTION = "test_collection"


# ==================== 測試環境配置 ====================

@pytest.fixture(scope="session")
def test_env() -> Dict[str, str]:
    """測試環境配置"""
    return {
        "ARANGO_HOST": os.getenv("ARANGO_HOST", "http://localhost:8529"),
        "ARANGO_USER": os.getenv("ARANGO_USER", "root"),
        "ARANGO_PASSWORD": os.getenv("ARANGO_PASSWORD", ""),
        "ARANGO_DB": TEST_ARANGO_DB,
        "CHROMA_HOST": os.getenv("CHROMA_HOST", "http://localhost:8000"),
        "CHROMA_COLLECTION": TEST_CHROMA_COLLECTION,
    }


# ==================== 數據庫 Fixtures ====================

@pytest.fixture(scope="session")
def arangodb_client(test_env: Dict[str, str]) -> Generator[Optional[ArangoDBClient], None, None]:
    """創建 ArangoDB 客戶端（真實連接，用於集成測試）"""
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
def mock_arangodb_client() -> Mock:
    """模擬 ArangoDB 客戶端（用於單元測試）"""
    client = Mock(spec=ArangoDBClient)
    client.db = Mock()
    client.db.has_collection = Mock(return_value=True)
    client.db.collection = Mock(return_value=Mock())
    client.get_or_create_collection = Mock(return_value=Mock())
    client.connect = Mock()
    client.close = Mock()
    return client


@pytest.fixture
def mock_chromadb_client() -> Mock:
    """模擬 ChromaDB 客戶端（用於單元測試）"""
    client = Mock()
    client.get_collection = Mock(return_value=Mock())
    client.create_collection = Mock(return_value=Mock())
    return client


# ==================== LLM Mock Fixtures ====================

@pytest.fixture
def mock_router_llm_response() -> SemanticUnderstandingOutput:
    """模擬 Router LLM 響應（L1 語義理解輸出）"""
    return SemanticUnderstandingOutput(
        topics=["document", "system_design"],
        entities=["Document Editing Agent", "API Spec"],
        action_signals=["design", "refine", "structure"],
        modality="instruction",
        certainty=0.92,
    )


@pytest.fixture
def mock_router_llm(mock_router_llm_response):
    """模擬 Router LLM 服務"""
    mock = AsyncMock()
    mock.route_v4 = AsyncMock(return_value=mock_router_llm_response)
    return mock


@pytest.fixture
def mock_task_planner_llm():
    """模擬 Task Planner LLM 服務（L3 任務規劃）"""
    mock = AsyncMock()
    mock.plan = AsyncMock(
        return_value=TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="document_editing",
                    agent="document-editing-agent",
                    depends_on=[],
                ),
                TaskNode(
                    id="T2",
                    capability="code_generation",
                    agent="code-generation-agent",
                    depends_on=["T1"],
                ),
            ],
            reasoning="Generated task DAG for document editing and code generation",
        )
    )
    return mock


# ==================== Orchestrator Mock Fixtures ====================

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
def mock_orchestrator_failure():
    """模擬 Orchestrator 執行失敗"""
    mock = AsyncMock(spec=AgentOrchestrator)
    mock.execute_task = AsyncMock(
        return_value={
            "success": False,
            "error": "Task execution failed",
            "agent_id": "document-editing-agent",
            "execution_time_ms": 50,
        }
    )
    return mock


@pytest.fixture
def mock_orchestrator_timeout():
    """模擬 Orchestrator 執行超時"""
    async def timeout_task(*args, **kwargs):
        import asyncio
        await asyncio.sleep(0.1)
        raise TimeoutError("Task execution timeout")

    mock = AsyncMock(spec=AgentOrchestrator)
    mock.execute_task = timeout_task
    return mock


# ==================== Security Agent Mock Fixtures ====================

@pytest.fixture
def mock_security_agent_allowed():
    """模擬 Security Agent 權限檢查 - 允許"""
    mock = AsyncMock()
    mock.check_permission = AsyncMock(
        return_value={
            "allowed": True,
            "requires_confirmation": False,
            "risk_level": "low",
            "reasons": [],
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
def mock_security_agent_confirmation_required():
    """模擬 Security Agent 權限檢查 - 需要確認"""
    mock = AsyncMock()
    mock.check_permission = AsyncMock(
        return_value={
            "allowed": True,
            "requires_confirmation": True,
            "risk_level": "high",
            "reasons": ["This is a high-risk operation that requires user confirmation"],
        }
    )
    return mock


# ==================== Task Analyzer Fixtures ====================

@pytest.fixture
def task_analyzer() -> TaskAnalyzer:
    """創建 TaskAnalyzer 實例"""
    return TaskAnalyzer()


@pytest.fixture
def orchestrator() -> AgentOrchestrator:
    """創建 AgentOrchestrator 實例"""
    return AgentOrchestrator()


# ==================== 測試數據 Fixtures ====================

@pytest.fixture
def sample_task_request() -> Dict[str, Any]:
    """示例任務請求"""
    return {
        "task": "編輯 API 規格文檔，添加新的端點定義",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
        "session_id": "test_session_123",
    }


@pytest.fixture
def sample_simple_query() -> Dict[str, Any]:
    """簡單查詢任務"""
    return {
        "task": "現在幾點？",
        "context": {"user_id": "test_user_123"},
        "user_id": "test_user_123",
    }


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
def sample_config_task() -> Dict[str, Any]:
    """配置操作任務"""
    return {
        "task": "查詢 GenAI 租戶策略配置",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_complex_task() -> Dict[str, Any]:
    """複雜多步驟任務"""
    return {
        "task": "分析用戶數據並生成報告，然後發送郵件通知",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_high_risk_task() -> Dict[str, Any]:
    """高風險任務（觸發風險檢查）"""
    return {
        "task": "刪除所有用戶數據並清空數據庫",
        "context": {"user_id": "test_user_123", "tenant_id": "test_tenant_123"},
        "user_id": "test_user_123",
    }


@pytest.fixture
def sample_general_query_task() -> Dict[str, Any]:
    """通用查詢任務（Fallback Intent）"""
    return {
        "task": "什麼是 AI-Box？",
        "context": {"user_id": "test_user_123"},
        "user_id": "test_user_123",
    }


# ==================== Intent Registry 測試數據 ====================

@pytest.fixture
def sample_intent_data() -> Dict[str, Any]:
    """示例 Intent 數據"""
    return {
        "name": "modify_document",
        "domain": "system_architecture",
        "target": "Document Editing Agent",
        "output_format": ["Engineering Spec"],
        "depth": "Advanced",
        "version": "1.0.0",
        "default_version": True,
        "is_active": True,
    }


# ==================== Capability Registry 測試數據 ====================

@pytest.fixture
def sample_capability_data() -> List[Dict[str, Any]]:
    """示例 Capability 數據"""
    return [
        {
            "name": "document_editing",
            "agent": "document-editing-agent",
            "description": "編輯文檔內容",
            "input": ["document_path", "editing_instructions"],
            "output": ["edited_document"],
            "constraints": {"max_file_size": "10MB"},
        },
        {
            "name": "code_generation",
            "agent": "code-generation-agent",
            "description": "生成代碼",
            "input": ["requirements", "language"],
            "output": ["source_code"],
            "constraints": {},
        },
    ]


# ==================== Policy Rules 測試數據 ====================

@pytest.fixture
def sample_policy_rules() -> List[Dict[str, Any]]:
    """示例 Policy Rules 數據"""
    return [
        {
            "rule_id": "rule_001",
            "type": "permission",
            "action": "allow",
            "conditions": {"user_role": "admin"},
        },
        {
            "rule_id": "rule_002",
            "type": "risk",
            "action": "require_confirmation",
            "conditions": {"risk_level": "high"},
        },
        {
            "rule_id": "rule_003",
            "type": "resource",
            "action": "limit",
            "conditions": {"max_tasks": 10, "time_window": "1h"},
        },
    ]


# ==================== 清理 Fixtures ====================

@pytest.fixture(autouse=True)
def cleanup_test_data():
    """自動清理測試數據（每個測試後執行）"""
    yield
    # 這裡可以添加清理邏輯，例如刪除測試創建的數據
    pass


# ==================== 性能測試 Fixtures ====================

@pytest.fixture
def performance_test_config() -> Dict[str, Any]:
    """性能測試配置"""
    return {
        "warmup_iterations": 3,
        "test_iterations": 10,
        "timeout_seconds": 30,
        "performance_thresholds": {
            "l1_latency_ms": 1000,
            "l2_latency_ms": 500,
            "l3_latency_ms": 2000,
            "l4_latency_ms": 500,
            "l5_latency_ms": 1000,
            "total_latency_ms": 5000,
        },
    }


# ==================== 壓力測試 Fixtures ====================

@pytest.fixture
def stress_test_config() -> Dict[str, Any]:
    """壓力測試配置"""
    return {
        "concurrent_requests": [10, 50, 100, 500],
        "test_duration_seconds": 60,
        "ramp_up_seconds": 10,
        "max_errors": 10,
    }
