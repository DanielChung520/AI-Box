# 代碼功能說明: P-T-A-O 資料模型單元測試
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""P-T-A-O 資料模型測試 — TDD Red Phase"""

from datetime import datetime
import pytest
from pydantic import ValidationError


# RED Phase: These tests will fail until models.py is implemented
class TestThoughtTrace:
    """ThoughtTrace 模型測試"""

    def test_thought_trace_creation(self):
        """測試 ThoughtTrace 基本建立"""
        from mm_agent.ptao.models import ThoughtTrace

        thought = ThoughtTrace(
            reasoning="根據用戶查詢料號 ABC-123，系統需要調用 Data-Agent 查詢庫存",
            intent_summary="查詢庫存",
            complexity="simple",
        )

        assert thought.reasoning == "根據用戶查詢料號 ABC-123，系統需要調用 Data-Agent 查詢庫存"
        assert thought.intent_summary == "查詢庫存"
        assert thought.complexity == "simple"
        assert isinstance(thought.timestamp, datetime)

    def test_thought_trace_with_complex(self):
        """測試 complex 類型 ThoughtTrace"""
        from mm_agent.ptao.models import ThoughtTrace

        thought = ThoughtTrace(
            reasoning="用戶查詢多個料號的庫存，並需要分析缺料情況，生成採購建議",
            intent_summary="複雜庫存分析",
            complexity="complex",
        )

        assert thought.complexity == "complex"

    def test_thought_trace_complexity_validation(self):
        """測試 complexity 欄位只允許 simple 或 complex"""
        from mm_agent.ptao.models import ThoughtTrace

        with pytest.raises(ValidationError):
            ThoughtTrace(
                reasoning="test",
                intent_summary="test",
                complexity="invalid",  # type: ignore
            )

    def test_thought_trace_timestamp_auto_set(self):
        """測試 timestamp 自動設置"""
        from mm_agent.ptao.models import ThoughtTrace

        before = datetime.now()
        thought = ThoughtTrace(
            reasoning="test reasoning",
            intent_summary="test",
            complexity="simple",
        )
        after = datetime.now()

        assert before <= thought.timestamp <= after

    def test_thought_trace_empty_reasoning(self):
        """測試空 reasoning 不被允許"""
        from mm_agent.ptao.models import ThoughtTrace

        with pytest.raises(ValidationError):
            ThoughtTrace(
                reasoning="",  # Empty
                intent_summary="test",
                complexity="simple",
            )


class TestObservation:
    """Observation 模型測試"""

    def test_observation_success_creation(self):
        """測試 Observation 成功建立（有 data）"""
        from mm_agent.ptao.models import Observation

        obs = Observation(
            source="data_agent",
            success=True,
            data={"part_number": "ABC-123", "stock": 100},
            duration_ms=45.2,
        )

        assert obs.source == "data_agent"
        assert obs.success is True
        assert obs.data == {"part_number": "ABC-123", "stock": 100}
        assert obs.error is None
        assert obs.duration_ms == 45.2

    def test_observation_failure_creation(self):
        """測試 Observation 失敗建立（有 error）"""
        from mm_agent.ptao.models import Observation

        obs = Observation(
            source="data_agent",
            success=False,
            error="Connection timeout to Datalake",
            duration_ms=5000.0,
        )

        assert obs.success is False
        assert obs.error == "Connection timeout to Datalake"
        assert obs.data is None

    def test_observation_requires_data_or_error(self):
        """測試 Observation 需要 data 或 error 之一"""
        from mm_agent.ptao.models import Observation

        # 這應該在驗證中被捕捉
        # success=True 時需要 data，success=False 時需要 error
        with pytest.raises(ValidationError):
            Observation(
                source="test",
                success=True,
                duration_ms=100.0,
                # Missing data when success=True
            )

    def test_observation_zero_duration(self):
        """測試 duration_ms 可以是 0"""
        from mm_agent.ptao.models import Observation

        obs = Observation(
            source="cache",
            success=True,
            data={},
            duration_ms=0.0,
        )

        assert obs.duration_ms == 0.0

    def test_observation_large_data(self):
        """測試 Observation 可處理大型 data 字典"""
        from mm_agent.ptao.models import Observation

        large_data = {f"key_{i}": f"value_{i}" for i in range(100)}

        obs = Observation(
            source="query",
            success=True,
            data=large_data,
            duration_ms=123.45,
        )

        assert len(obs.data) == 100


class TestDecisionEntry:
    """DecisionEntry 模型測試"""

    def test_decision_entry_creation(self):
        """測試 DecisionEntry 基本建立"""
        from mm_agent.ptao.models import DecisionEntry

        entry = DecisionEntry(
            phase="plan",
            action="call_data_agent",
            rationale="用戶查詢庫存，需要從 Data-Agent 獲取數據",
        )

        assert entry.phase == "plan"
        assert entry.action == "call_data_agent"
        assert entry.rationale == "用戶查詢庫存，需要從 Data-Agent 獲取數據"
        assert isinstance(entry.timestamp, datetime)

    def test_decision_entry_all_phases(self):
        """測試所有 phase 類型"""
        from mm_agent.ptao.models import DecisionEntry

        phases = ["plan", "think", "act", "observe"]

        for phase in phases:
            entry = DecisionEntry(
                phase=phase,  # type: ignore
                action=f"action_{phase}",
                rationale=f"rationale_{phase}",
            )
            assert entry.phase == phase

    def test_decision_entry_invalid_phase(self):
        """測試無效 phase 被拒絕"""
        from mm_agent.ptao.models import DecisionEntry

        with pytest.raises(ValidationError):
            DecisionEntry(
                phase="invalid_phase",  # type: ignore
                action="test",
                rationale="test",
            )

    def test_decision_entry_timestamp_auto_set(self):
        """測試 timestamp 自動設置"""
        from mm_agent.ptao.models import DecisionEntry

        before = datetime.now()
        entry = DecisionEntry(
            phase="act",
            action="test_action",
            rationale="test",
        )
        after = datetime.now()

        assert before <= entry.timestamp <= after


class TestDecisionLog:
    """DecisionLog 模型測試"""

    def test_decision_log_creation(self):
        """測試 DecisionLog 基本建立"""
        from mm_agent.ptao.models import DecisionLog

        log = DecisionLog(entries=[])

        assert log.entries == []

    def test_decision_log_add_entry(self):
        """測試 DecisionLog.add_entry() 方法"""
        from mm_agent.ptao.models import DecisionLog, DecisionEntry

        log = DecisionLog(entries=[])

        entry1 = DecisionEntry(
            phase="plan",
            action="analyze_query",
            rationale="分析用戶查詢",
        )
        log.add_entry(entry1)

        assert len(log.entries) == 1
        assert log.entries[0] == entry1

    def test_decision_log_add_multiple_entries(self):
        """測試多個 add_entry 調用"""
        from mm_agent.ptao.models import DecisionLog, DecisionEntry

        log = DecisionLog(entries=[])

        entries = [
            DecisionEntry(phase="plan", action="analyze", rationale="分析"),
            DecisionEntry(phase="think", action="classify", rationale="分類"),
            DecisionEntry(phase="act", action="execute", rationale="執行"),
            DecisionEntry(phase="observe", action="verify", rationale="驗證"),
        ]

        for entry in entries:
            log.add_entry(entry)

        assert len(log.entries) == 4
        assert log.entries == entries

    def test_decision_log_with_initial_entries(self):
        """測試建立時帶有初始 entries"""
        from mm_agent.ptao.models import DecisionLog, DecisionEntry

        entries = [
            DecisionEntry(phase="plan", action="test1", rationale="reason1"),
            DecisionEntry(phase="think", action="test2", rationale="reason2"),
        ]

        log = DecisionLog(entries=entries)

        assert len(log.entries) == 2
        assert log.entries == entries

    def test_decision_log_add_entry_preserves_order(self):
        """測試 add_entry 保持順序"""
        from mm_agent.ptao.models import DecisionLog, DecisionEntry

        log = DecisionLog(entries=[])

        phases = ["plan", "think", "act", "observe"]

        for i, phase in enumerate(phases):
            log.add_entry(
                DecisionEntry(
                    phase=phase,  # type: ignore
                    action=f"action_{i}",
                    rationale=f"reason_{i}",
                )
            )

        assert len(log.entries) == 4
        for i, entry in enumerate(log.entries):
            assert entry.phase == phases[i]


class TestPTAOResult:
    """PTAOResult 模型測試"""

    def test_ptao_result_creation(self):
        """測試 PTAOResult 基本建立"""
        from mm_agent.ptao.models import PTAOResult, ThoughtTrace, Observation, DecisionLog

        thought = ThoughtTrace(
            reasoning="test reasoning",
            intent_summary="test intent",
            complexity="simple",
        )

        obs = Observation(
            source="test_source",
            success=True,
            data={"key": "value"},
            duration_ms=10.0,
        )

        decision_log = DecisionLog(entries=[])

        result = PTAOResult(
            thought=thought,
            observation=obs,
            decision_log=decision_log,
            raw_result={"status": "success"},
        )

        assert result.thought == thought
        assert result.observation == obs
        assert result.decision_log == decision_log
        assert result.raw_result == {"status": "success"}

    def test_ptao_result_full_workflow(self):
        """測試完整 P-T-A-O 工作流程的結果"""
        from mm_agent.ptao.models import (
            PTAOResult,
            ThoughtTrace,
            Observation,
            DecisionLog,
            DecisionEntry,
        )

        thought = ThoughtTrace(
            reasoning="用戶查詢料號 ABC-123 的庫存，需要調用 Data-Agent",
            intent_summary="查詢庫存",
            complexity="simple",
        )

        obs = Observation(
            source="data_agent",
            success=True,
            data={"part_number": "ABC-123", "stock_quantity": 100},
            duration_ms=250.5,
        )

        decision_log = DecisionLog(entries=[])
        decision_log.add_entry(
            DecisionEntry(
                phase="plan",
                action="call_data_agent",
                rationale="用戶查詢需要數據支持",
            )
        )
        decision_log.add_entry(
            DecisionEntry(
                phase="observe",
                action="validate_result",
                rationale="驗證返回結果有效性",
            )
        )

        result = PTAOResult(
            thought=thought,
            observation=obs,
            decision_log=decision_log,
            raw_result={
                "task_id": "task_123",
                "status": "completed",
                "data": obs.data,
            },
        )

        assert len(result.decision_log.entries) == 2
        assert result.observation.success is True
        assert result.thought.complexity == "simple"

    def test_ptao_result_with_failed_observation(self):
        """測試 PTAO Result 包含失敗 observation"""
        from mm_agent.ptao.models import (
            PTAOResult,
            ThoughtTrace,
            Observation,
            DecisionLog,
        )

        thought = ThoughtTrace(
            reasoning="試圖查詢但發生錯誤",
            intent_summary="查詢庫存",
            complexity="simple",
        )

        obs = Observation(
            source="data_agent",
            success=False,
            error="Database connection failed",
            duration_ms=5000.0,
        )

        decision_log = DecisionLog(entries=[])

        result = PTAOResult(
            thought=thought,
            observation=obs,
            decision_log=decision_log,
            raw_result={"status": "error", "error": obs.error},
        )

        assert result.observation.success is False
        assert result.observation.error == "Database connection failed"


class TestModelSerialization:
    """模型序列化測試"""

    def test_ptao_result_dict_conversion(self):
        """測試 PTAOResult 轉 dict"""
        from mm_agent.ptao.models import PTAOResult, ThoughtTrace, Observation, DecisionLog

        thought = ThoughtTrace(
            reasoning="test",
            intent_summary="test",
            complexity="simple",
        )
        obs = Observation(
            source="test",
            success=True,
            data={"test": "data"},
            duration_ms=1.0,
        )
        decision_log = DecisionLog(entries=[])

        result = PTAOResult(
            thought=thought,
            observation=obs,
            decision_log=decision_log,
            raw_result={},
        )

        result_dict = result.model_dump()

        assert "thought" in result_dict
        assert "observation" in result_dict
        assert "decision_log" in result_dict
        assert "raw_result" in result_dict

    def test_ptao_result_json_conversion(self):
        """測試 PTAOResult 轉 JSON"""
        from mm_agent.ptao.models import PTAOResult, ThoughtTrace, Observation, DecisionLog

        thought = ThoughtTrace(
            reasoning="test reasoning",
            intent_summary="test",
            complexity="simple",
        )
        obs = Observation(
            source="test",
            success=True,
            data={"result": "ok"},
            duration_ms=100.0,
        )
        decision_log = DecisionLog(entries=[])

        result = PTAOResult(
            thought=thought,
            observation=obs,
            decision_log=decision_log,
            raw_result={"status": "ok"},
        )

        json_str = result.model_dump_json()

        assert isinstance(json_str, str)
        assert "thought" in json_str
        assert "observation" in json_str
