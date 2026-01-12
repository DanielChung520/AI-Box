# 代碼功能說明: 階段1核心功能驗證測試
# 創建日期: 2026-01-08
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-08

"""階段1核心功能驗證測試

驗證階段1實現的核心功能是否正常工作。
"""

import pytest

from agents.services.orchestrator.models import TaskStatus
from agents.services.orchestrator.task_tracker import TaskTracker
from agents.task_analyzer.clarification import ClarificationService
from agents.task_analyzer.models import TaskAnalysisRequest


class TestClarificationService:
    """測試澄清服務"""

    def test_clarification_service_init(self):
        """測試澄清服務初始化"""
        service = ClarificationService()
        assert service is not None
        assert service.llm_router is not None

    @pytest.mark.asyncio
    async def test_extract_slots(self):
        """測試槽位提取"""
        service = ClarificationService()
        slots = await service.extract_slots(
            instruction="設置租戶 A 的限流為 500",
            task_type="config",
            required_slots=["level", "tenant_id", "config_data"],
        )
        assert "slots" in slots
        assert "missing_slots" in slots


class TestTaskTracker:
    """測試任務追蹤器"""

    def test_task_tracker_init(self):
        """測試任務追蹤器初始化"""
        tracker = TaskTracker(use_arangodb=False)  # 使用內存模式進行測試
        assert tracker is not None
        assert tracker.use_arangodb is False

    def test_create_task(self):
        """測試創建任務"""
        tracker = TaskTracker(use_arangodb=False)
        task_id = tracker.create_task(
            instruction="測試任務",
            target_agent_id="test_agent",
            user_id="test_user",
        )
        assert task_id is not None
        assert len(task_id) > 0

    def test_get_task_status(self):
        """測試獲取任務狀態"""
        tracker = TaskTracker(use_arangodb=False)
        task_id = tracker.create_task(
            instruction="測試任務",
            target_agent_id="test_agent",
            user_id="test_user",
        )
        task_record = tracker.get_task_status(task_id)
        assert task_record is not None
        assert task_record.task_id == task_id
        assert task_record.status == TaskStatus.PENDING

    def test_update_task_status(self):
        """測試更新任務狀態"""
        tracker = TaskTracker(use_arangodb=False)
        task_id = tracker.create_task(
            instruction="測試任務",
            target_agent_id="test_agent",
            user_id="test_user",
        )
        success = tracker.update_task_status(
            task_id, TaskStatus.COMPLETED, result={"output": "success"}
        )
        assert success is True
        task_record = tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.COMPLETED
        assert task_record.result == {"output": "success"}


class TestTaskAnalysisRequest:
    """測試任務分析請求模型"""

    def test_task_analysis_request_with_specified_agent(self):
        """測試帶有指定Agent的任務分析請求"""
        request = TaskAnalysisRequest(
            task="測試任務",
            specified_agent_id="test_agent",
        )
        assert request.specified_agent_id == "test_agent"
        assert request.task == "測試任務"
