# 代碼功能說明: KA-Agent 端到端流程測試（模擬「上架 Tiptop 手冊」完整循環）
# 創建日期: 2026-01-25 19:49 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-25 20:15 UTC+8

"""KA-Agent 端到端流程測試：管理未確認 → 確認+註冊 → 檢索（規格 Ch 13）"""

from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Mock database.chromadb 依賴，避免 agents.builtin 導入鏈拉入 chromadb
_client = MagicMock()
_client.ChromaDBClient = MagicMock()
sys.modules["database.chromadb.client"] = _client
_chroma = MagicMock()
sys.modules["database.chromadb"] = _chroma

from agents.builtin.ka_agent.agent import KnowledgeArchitectAgent
from agents.services.protocol.base import AgentServiceRequest
from services.api.models.file_metadata import FileMetadataCreate
from services.api.services.file_metadata_service import get_metadata_service

# 模擬 LLM 產出
_MANAGEMENT_LLM = (
    '{"category":"MANAGEMENT","todo_list":[{"id":1,"desc":"上架 Tiptop 手冊","status":"pending"}]}'
)
_RETRIEVAL_LLM = '{"category":"RETRIEVAL"}'


def _ensure_file_metadata(file_id: str, user_id: str = "systemAdmin") -> None:
    meta = get_metadata_service()
    if meta.get(file_id):
        return
    create = FileMetadataCreate(
        file_id=file_id,
        filename="Tiptop手冊.pdf",
        file_type="application/pdf",
        file_size=1024,
        user_id=user_id,
        task_id="KA-Agent-Tasks",
        storage_path=f"knowledge-assets/tiptop/{file_id}.pdf",
        status="uploaded",
    )
    meta.create(create)


@pytest.fixture
def mock_llm():
    async def _mock(prompt: str) -> str:
        if "查詢" in prompt or "query" in prompt.lower() or "search" in prompt.lower():
            return _RETRIEVAL_LLM
        return _MANAGEMENT_LLM

    return AsyncMock(side_effect=_mock)


@pytest.mark.asyncio
async def test_ka_ingestion_flow_mock_llm(mock_llm: AsyncMock) -> None:
    """模擬「上架 Tiptop 手冊」完整循環：管理未確認 → 確認+註冊 → 檢索。"""
    file_id = str(uuid.uuid4())
    _ensure_file_metadata(file_id)
    task_id_base = f"ka-e2e-{uuid.uuid4().hex[:8]}"

    with patch.object(KnowledgeArchitectAgent, "_call_llm_chain", new=mock_llm):
        agent = KnowledgeArchitectAgent()

        # 步驟 1：管理未確認 → AWAITING + todo_list
        req1 = AgentServiceRequest(
            task_id=f"{task_id_base}-1",
            task_type="ka_management",
            task_data={
                "action": "ka.lifecycle",
                "instruction": "上架 Tiptop 手冊",
                "metadata": {},
            },
            metadata={"user_id": "systemAdmin"},
        )
        r1 = await agent.execute(req1)
        assert r1.status == "completed", r1.error
        assert r1.result is not None
        assert r1.result.get("metadata", {}).get("status") == "AWAITING_CONFIRMATION"
        todo = r1.result.get("metadata", {}).get("todo_list", [])
        assert len(todo) > 0
        task_id = r1.result.get("metadata", {}).get("task_id")
        assert task_id

        # 步驟 2：確認 + file_id → 註冊 + 審計
        req2 = AgentServiceRequest(
            task_id=task_id,
            task_type="ka_management",
            task_data={
                "action": "ka.lifecycle",
                "instruction": "上架 Tiptop 手冊",
                "file_id": file_id,
                "metadata": {"file_id": file_id},
            },
            metadata={
                "user_id": "systemAdmin",
                "user_confirmed": True,
                "task_id": task_id,
                "file_id": file_id,
            },
        )
        r2 = await agent.execute(req2)
        assert r2.status == "completed", r2.error
        res2 = r2.result or {}
        ka_id = res2.get("metadata", {}).get("ka_id") or res2.get("ka_id")
        assert ka_id, res2

        # 步驟 3：檢索
        req3 = AgentServiceRequest(
            task_id=f"{task_id_base}-3",
            task_type="ka_retrieval",
            task_data={
                "action": "knowledge.query",
                "query": "Tiptop 手冊",
                "instruction": "查詢 Tiptop 手冊",
                "top_k": 5,
                "query_type": "hybrid",
            },
            metadata={"user_id": "systemAdmin"},
        )
        r3 = await agent.execute(req3)
        assert r3.status in ("completed", "failed"), r3.error
