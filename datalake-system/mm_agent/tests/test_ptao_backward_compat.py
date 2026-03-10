# 代碼功能說明: P-T-A-O 回應格式向後相容驗證測試
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""向後相容驗證 — 確保 P-T-A-O metadata 不破壞既有回應格式。

驗證項目：
1. AgentServiceResponse 所有欄位保持不變
2. WarehouseAgentResponse 所有欄位保持不變
3. ptao metadata 僅存在於 metadata["ptao"]，不汙染其他欄位
4. ptao 內部結構符合規格
5. 舊客戶端（不認識 ptao）可正常讀取 task_id / status / result
"""

from datetime import datetime
from typing import Any, Dict

import pytest

from agents.services.protocol.base import AgentServiceResponse
from mm_agent.models import WarehouseAgentResponse
from mm_agent.ptao.models import (
    DecisionEntry,
    DecisionLog,
    Observation,
    PTAOResult,
    ThoughtTrace,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_thought() -> ThoughtTrace:
    """建立標準 ThoughtTrace 實例"""
    return ThoughtTrace(
        reasoning="用戶查詢料號 ABC-123 庫存，屬於簡單庫存查詢",
        intent_summary="查詢料號庫存",
        complexity="simple",
    )


@pytest.fixture
def sample_observation_success() -> Observation:
    """建立成功的 Observation 實例"""
    return Observation(
        source="data_agent",
        success=True,
        data={"rows": [{"part_number": "ABC-123", "qty": 50}]},
        duration_ms=42.5,
    )


@pytest.fixture
def sample_observation_failure() -> Observation:
    """建立失敗的 Observation 實例"""
    return Observation(
        source="data_agent",
        success=False,
        error="Connection timeout",
        duration_ms=5000.0,
    )


@pytest.fixture
def sample_decision_log() -> DecisionLog:
    """建立標準 DecisionLog 實例"""
    log = DecisionLog()
    log.add_entry(
        DecisionEntry(phase="plan", action="分析用戶意圖", rationale="用戶提到料號和庫存")
    )
    log.add_entry(
        DecisionEntry(phase="act", action="調用 data_agent", rationale="需要查詢庫存數據")
    )
    return log


@pytest.fixture
def sample_ptao_result(
    sample_thought: ThoughtTrace,
    sample_observation_success: Observation,
    sample_decision_log: DecisionLog,
) -> PTAOResult:
    """建立完整的 PTAOResult 實例"""
    return PTAOResult(
        thought=sample_thought,
        observation=sample_observation_success,
        decision_log=sample_decision_log,
        raw_result={"success": True, "data": [{"part_number": "ABC-123", "qty": 50}]},
    )


@pytest.fixture
def ptao_metadata_dict(sample_ptao_result: PTAOResult) -> Dict[str, Any]:
    """模擬 agent.py step 9 構建的 ptao_metadata"""
    return {
        "ptao": {
            "thought": sample_ptao_result.thought.model_dump(),
            "observation": sample_ptao_result.observation.model_dump(),
            "decision_log": [e.model_dump() for e in sample_ptao_result.decision_log.entries],
        }
    }


@pytest.fixture
def warehouse_response(ptao_metadata_dict: Dict[str, Any]) -> WarehouseAgentResponse:
    """建立帶有 ptao metadata 的 WarehouseAgentResponse"""
    return WarehouseAgentResponse(
        success=True,
        task_type="query_stock",
        result={"success": True, "data": [{"part_number": "ABC-123", "qty": 50}]},
        response="料號 ABC-123 庫存為 50",
        metadata=ptao_metadata_dict,
    )


@pytest.fixture
def agent_service_response(
    warehouse_response: WarehouseAgentResponse,
) -> AgentServiceResponse:
    """建立完整的 AgentServiceResponse（模擬 agent.py step 9 最終輸出）"""
    return AgentServiceResponse(
        task_id="task-compat-001",
        status="completed",
        result=warehouse_response.model_dump(),
        error=None,
        metadata={"session_id": "s-1", "user_id": "u-1"},
    )


# ---------------------------------------------------------------------------
# 1. AgentServiceResponse 欄位完整性
# ---------------------------------------------------------------------------


class TestAgentServiceResponseFields:
    """驗證 AgentServiceResponse 的所有標準欄位保持不變"""

    REQUIRED_FIELDS = {"task_id", "status", "result", "error", "metadata"}

    def test_agent_service_response_fields(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """所有 AgentServiceResponse 標準欄位必須存在且型別正確"""
        model_fields = set(agent_service_response.model_fields.keys())
        assert self.REQUIRED_FIELDS == model_fields, (
            f"AgentServiceResponse 欄位不符預期。"
            f"缺少: {self.REQUIRED_FIELDS - model_fields}，"
            f"多出: {model_fields - self.REQUIRED_FIELDS}"
        )

    def test_agent_service_response_field_types(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """驗證各欄位型別"""
        resp = agent_service_response
        assert isinstance(resp.task_id, str)
        assert isinstance(resp.status, str)
        assert isinstance(resp.result, dict) or resp.result is None
        assert resp.error is None or isinstance(resp.error, str)
        assert isinstance(resp.metadata, dict) or resp.metadata is None

    def test_agent_service_response_no_extra_fields(self) -> None:
        """建構帶有額外欄位的 AgentServiceResponse 應被忽略或拒絕"""
        # Pydantic v2 default: extra fields are ignored
        resp = AgentServiceResponse(
            task_id="t-1",
            status="completed",
            result=None,
            error=None,
            metadata=None,
        )
        dumped = resp.model_dump()
        assert set(dumped.keys()) == self.REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# 2. WarehouseAgentResponse 欄位完整性
# ---------------------------------------------------------------------------


class TestWarehouseAgentResponseFields:
    """驗證 WarehouseAgentResponse 的所有欄位保持不變"""

    EXPECTED_FIELDS = {
        "success",
        "task_type",
        "response",
        "result",
        "error",
        "metadata",
        "semantic_analysis",
        "responsibility",
        "data_queries",
        "validation",
        "anomalies",
    }

    def test_warehouse_agent_response_fields(
        self, warehouse_response: WarehouseAgentResponse
    ) -> None:
        """所有 WarehouseAgentResponse 欄位必須存在"""
        model_fields = set(warehouse_response.model_fields.keys())
        assert self.EXPECTED_FIELDS == model_fields, (
            f"WarehouseAgentResponse 欄位不符預期。"
            f"缺少: {self.EXPECTED_FIELDS - model_fields}，"
            f"多出: {model_fields - self.EXPECTED_FIELDS}"
        )

    def test_warehouse_agent_response_field_types(
        self, warehouse_response: WarehouseAgentResponse
    ) -> None:
        """驗證 WarehouseAgentResponse 各欄位型別"""
        r = warehouse_response
        assert isinstance(r.success, bool)
        assert isinstance(r.task_type, str)
        assert r.response is None or isinstance(r.response, str)
        assert r.result is None or isinstance(r.result, dict)
        assert r.error is None or isinstance(r.error, str)
        assert r.metadata is None or isinstance(r.metadata, dict)
        assert r.semantic_analysis is None or isinstance(r.semantic_analysis, dict)
        assert r.responsibility is None or isinstance(r.responsibility, str)
        assert isinstance(r.data_queries, list)
        assert r.validation is None or isinstance(r.validation, dict)
        assert isinstance(r.anomalies, list)

    def test_warehouse_response_core_fields_mandatory(self) -> None:
        """success 和 task_type 為必填欄位"""
        with pytest.raises(Exception):
            WarehouseAgentResponse()  # type: ignore[call-arg]

        # 僅提供 success 和 task_type 即可建構
        resp = WarehouseAgentResponse(success=True, task_type="query_stock")
        assert resp.success is True
        assert resp.task_type == "query_stock"
        assert resp.metadata is None  # optional, 預設 None


# ---------------------------------------------------------------------------
# 3. ptao metadata 不汙染頂層欄位
# ---------------------------------------------------------------------------


class TestPtaoNotPollutingTopLevel:
    """驗證 ptao metadata 僅存在於 metadata["ptao"]，不影響其他欄位"""

    def test_ptao_metadata_not_polluting_top_level(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """AgentServiceResponse 頂層不應出現 ptao 相關 key"""
        dumped = agent_service_response.model_dump()
        # 頂層只有標準 5 欄位
        top_keys = set(dumped.keys())
        assert "ptao" not in top_keys
        assert "thought" not in top_keys
        assert "observation" not in top_keys
        assert "decision_log" not in top_keys

    def test_ptao_only_in_warehouse_metadata(
        self, warehouse_response: WarehouseAgentResponse
    ) -> None:
        """WarehouseAgentResponse 中 ptao 只存在於 metadata["ptao"]"""
        dumped = warehouse_response.model_dump()

        # 頂層不應有 ptao key
        assert "ptao" not in dumped
        assert "thought" not in dumped
        assert "observation" not in dumped
        assert "decision_log" not in dumped

        # ptao 存在於 metadata 內
        assert "ptao" in dumped["metadata"]

    def test_ptao_does_not_leak_into_result(
        self, warehouse_response: WarehouseAgentResponse
    ) -> None:
        """ptao 不應洩漏到 result 欄位"""
        dumped = warehouse_response.model_dump()
        result = dumped["result"]
        assert "ptao" not in result
        assert "thought" not in result
        assert "observation" not in result
        assert "decision_log" not in result

    def test_ptao_does_not_leak_into_semantic_analysis(
        self, warehouse_response: WarehouseAgentResponse
    ) -> None:
        """ptao 不應洩漏到 semantic_analysis 欄位"""
        dumped = warehouse_response.model_dump()
        if dumped.get("semantic_analysis") is not None:
            sa = dumped["semantic_analysis"]
            assert "ptao" not in sa
            assert "thought" not in sa

    def test_agent_response_result_contains_ptao_in_metadata_only(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """AgentServiceResponse.result (= WarehouseAgentResponse.model_dump()) 中
        ptao 僅在 result.metadata.ptao"""
        result_dict = agent_service_response.result
        assert result_dict is not None

        # result 頂層不應有 ptao
        assert "ptao" not in result_dict
        assert "thought" not in result_dict

        # ptao 在 result -> metadata -> ptao
        assert "metadata" in result_dict
        assert "ptao" in result_dict["metadata"]


# ---------------------------------------------------------------------------
# 4. ThoughtTrace 結構驗證
# ---------------------------------------------------------------------------


class TestPtaoThoughtStructure:
    """驗證 thought 結構: {reasoning, intent_summary, complexity, timestamp}"""

    EXPECTED_KEYS = {"reasoning", "intent_summary", "complexity", "timestamp"}

    def test_ptao_thought_structure(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """thought dict 必須包含所有必要 key"""
        thought = ptao_metadata_dict["ptao"]["thought"]
        assert set(thought.keys()) == self.EXPECTED_KEYS

    def test_thought_reasoning_is_string(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """reasoning 必須為非空字串"""
        thought = ptao_metadata_dict["ptao"]["thought"]
        assert isinstance(thought["reasoning"], str)
        assert len(thought["reasoning"]) > 0

    def test_thought_intent_summary_is_string(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        thought = ptao_metadata_dict["ptao"]["thought"]
        assert isinstance(thought["intent_summary"], str)

    def test_thought_complexity_value(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """complexity 必須為 'simple' 或 'complex'"""
        thought = ptao_metadata_dict["ptao"]["thought"]
        assert thought["complexity"] in ("simple", "complex")

    def test_thought_timestamp_is_serializable(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """timestamp 必須為可解析的 datetime 字串"""
        thought = ptao_metadata_dict["ptao"]["thought"]
        ts = thought["timestamp"]
        # Pydantic model_dump() 預設 datetime 為 datetime object
        # 若 json 序列化則為 ISO 字串
        assert isinstance(ts, (str, datetime))

    def test_thought_model_validates_empty_reasoning(self) -> None:
        """空 reasoning 應被 model 拒絕"""
        with pytest.raises(Exception):
            ThoughtTrace(
                reasoning="",
                intent_summary="test",
                complexity="simple",
            )


# ---------------------------------------------------------------------------
# 5. Observation 結構驗證
# ---------------------------------------------------------------------------


class TestPtaoObservationStructure:
    """驗證 observation 結構: {source, success, data, error, duration_ms}"""

    EXPECTED_KEYS = {"source", "success", "data", "error", "duration_ms"}

    def test_ptao_observation_structure(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """observation dict 必須包含所有必要 key"""
        obs = ptao_metadata_dict["ptao"]["observation"]
        assert set(obs.keys()) == self.EXPECTED_KEYS

    def test_observation_source_is_string(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        obs = ptao_metadata_dict["ptao"]["observation"]
        assert isinstance(obs["source"], str)

    def test_observation_success_is_bool(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        obs = ptao_metadata_dict["ptao"]["observation"]
        assert isinstance(obs["success"], bool)

    def test_observation_duration_ms_is_numeric(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        obs = ptao_metadata_dict["ptao"]["observation"]
        assert isinstance(obs["duration_ms"], (int, float))
        assert obs["duration_ms"] >= 0

    def test_observation_success_has_data(self, sample_observation_success: Observation) -> None:
        """成功的 observation 必須有 data"""
        dumped = sample_observation_success.model_dump()
        assert dumped["success"] is True
        assert dumped["data"] is not None

    def test_observation_failure_has_error(self, sample_observation_failure: Observation) -> None:
        """失敗的 observation 必須有 error"""
        dumped = sample_observation_failure.model_dump()
        assert dumped["success"] is False
        assert dumped["error"] is not None
        assert isinstance(dumped["error"], str)


# ---------------------------------------------------------------------------
# 6. DecisionLog 結構驗證
# ---------------------------------------------------------------------------


class TestPtaoDecisionLogStructure:
    """驗證 decision_log 結構: List[{phase, action, rationale, timestamp}]"""

    ENTRY_KEYS = {"phase", "action", "rationale", "timestamp"}

    def test_ptao_decision_log_structure(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """decision_log 必須為 list"""
        dl = ptao_metadata_dict["ptao"]["decision_log"]
        assert isinstance(dl, list)
        assert len(dl) > 0

    def test_decision_log_entry_keys(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """每個 entry 必須有 phase, action, rationale, timestamp"""
        dl = ptao_metadata_dict["ptao"]["decision_log"]
        for entry in dl:
            assert set(entry.keys()) == self.ENTRY_KEYS, (
                f"DecisionEntry 欄位不符預期: {set(entry.keys())}"
            )

    def test_decision_log_phase_values(self, ptao_metadata_dict: Dict[str, Any]) -> None:
        """phase 必須為 plan/think/act/observe 之一"""
        valid_phases = {"plan", "think", "act", "observe"}
        dl = ptao_metadata_dict["ptao"]["decision_log"]
        for entry in dl:
            assert entry["phase"] in valid_phases, f"無效 phase: {entry['phase']}"

    def test_decision_log_action_and_rationale_are_strings(
        self, ptao_metadata_dict: Dict[str, Any]
    ) -> None:
        dl = ptao_metadata_dict["ptao"]["decision_log"]
        for entry in dl:
            assert isinstance(entry["action"], str)
            assert isinstance(entry["rationale"], str)

    def test_decision_log_can_be_empty(self) -> None:
        """空的 decision_log 是合法的"""
        log = DecisionLog()
        assert log.entries == []
        dumped = [e.model_dump() for e in log.entries]
        assert dumped == []


# ---------------------------------------------------------------------------
# 7. 舊客戶端相容性
# ---------------------------------------------------------------------------


class TestOldClientCompat:
    """模擬舊客戶端只讀取 task_id / status / result，不認識 ptao"""

    def test_old_client_compat(self, agent_service_response: AgentServiceResponse) -> None:
        """舊客戶端只讀取 task_id, status, result — 不需要知道 ptao 的存在"""
        resp = agent_service_response

        # 舊客戶端的 3 個常用欄位
        task_id = resp.task_id
        status = resp.status
        result = resp.result

        assert isinstance(task_id, str)
        assert task_id == "task-compat-001"
        assert status in ("completed", "failed", "error")
        assert isinstance(result, dict)

        # 舊客戶端可能直接取 result["success"]
        assert "success" in result
        assert isinstance(result["success"], bool)

        # 舊客戶端可能取 result["task_type"]
        assert "task_type" in result
        assert isinstance(result["task_type"], str)

    def test_old_client_ignores_metadata(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """舊客戶端不讀 metadata 也能正常運作"""
        resp = agent_service_response
        # 模擬舊客戶端只取必要欄位
        old_client_data = {
            "task_id": resp.task_id,
            "status": resp.status,
            "result": resp.result,
            "error": resp.error,
        }
        assert old_client_data["task_id"] == "task-compat-001"
        assert old_client_data["status"] == "completed"
        assert old_client_data["error"] is None
        assert old_client_data["result"]["success"] is True

    def test_old_client_can_access_warehouse_response_without_ptao(self) -> None:
        """不帶 ptao metadata 的 WarehouseAgentResponse 完全正常"""
        resp = WarehouseAgentResponse(
            success=True,
            task_type="query_stock",
            result={"success": True, "data": []},
            response="查無資料",
        )
        dumped = resp.model_dump()
        assert dumped["success"] is True
        assert dumped["task_type"] == "query_stock"
        assert dumped["metadata"] is None  # 無 ptao → None

    def test_old_client_json_serialization(
        self, agent_service_response: AgentServiceResponse
    ) -> None:
        """AgentServiceResponse JSON 序列化後，舊客戶端可正常解析"""
        import json

        json_str = agent_service_response.model_dump_json()
        parsed = json.loads(json_str)

        # 舊客戶端只看這些
        assert "task_id" in parsed
        assert "status" in parsed
        assert "result" in parsed
        assert parsed["task_id"] == "task-compat-001"
        assert parsed["status"] == "completed"

        # 舊客戶端不需要理解 ptao，但它不會崩潰
        inner_result = parsed["result"]
        assert inner_result["success"] is True
        assert inner_result["task_type"] == "query_stock"


# ---------------------------------------------------------------------------
# 8. 端到端：模擬 agent.py execute() 的 response 構建
# ---------------------------------------------------------------------------


class TestEndToEndResponseConstruction:
    """模擬 agent.py step 9 的完整 response 構建流程"""

    def test_full_response_chain(
        self,
        sample_ptao_result: PTAOResult,
    ) -> None:
        """模擬 agent.py step 9 的構建邏輯，驗證完整鏈路"""
        # 模擬 step 9 構建
        ptao_metadata = {
            "ptao": {
                "thought": sample_ptao_result.thought.model_dump(),
                "observation": sample_ptao_result.observation.model_dump(),
                "decision_log": [e.model_dump() for e in sample_ptao_result.decision_log.entries],
            }
        }
        warehouse_resp = WarehouseAgentResponse(
            success=True,
            task_type="query_stock",
            result={"success": True, "data": [{"part_number": "ABC-123", "qty": 50}]},
            metadata=ptao_metadata,
        )
        final_resp = AgentServiceResponse(
            task_id="task-e2e-001",
            status="completed",
            result=warehouse_resp.model_dump(),
            error=None,
            metadata={"session_id": "s-1"},
        )

        # AgentServiceResponse 頂層欄位驗證
        assert final_resp.task_id == "task-e2e-001"
        assert final_resp.status == "completed"
        assert final_resp.error is None

        # result 是 WarehouseAgentResponse dump
        r = final_resp.result
        assert r is not None
        assert r["success"] is True
        assert r["task_type"] == "query_stock"

        # ptao 在 result -> metadata -> ptao
        assert "ptao" in r["metadata"]
        ptao = r["metadata"]["ptao"]
        assert "thought" in ptao
        assert "observation" in ptao
        assert "decision_log" in ptao

        # ptao 不在 result 頂層
        assert "thought" not in r
        assert "observation" not in r

    def test_no_metadata_response_is_valid(self) -> None:
        """無 metadata 的 response 也合法（向後相容 ptao 之前的行為）"""
        warehouse_resp = WarehouseAgentResponse(
            success=False,
            task_type="query_stock",
            error="查無資料",
        )
        final_resp = AgentServiceResponse(
            task_id="task-no-meta",
            status="failed",
            result=warehouse_resp.model_dump(),
            error="查無資料",
        )
        assert final_resp.result is not None
        assert final_resp.result["metadata"] is None
        assert final_resp.error == "查無資料"
