# 代碼功能說明: Task Tracker 單元測試
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""Task Tracker 單元測試"""

import pytest

from agents.services.orchestrator.models import TaskStatus
from agents.services.orchestrator.task_tracker import TaskRecord, TaskTracker


class TestTaskTracker:
    """Task Tracker 測試類"""

    @pytest.fixture
    def task_tracker(self):
        """創建 TaskTracker 實例"""
        return TaskTracker()

    @pytest.fixture
    def sample_task_data(self):
        """示例任務數據"""
        return {
            "instruction": "查詢系統配置",
            "target_agent_id": "system_config_agent",
            "user_id": "user_123",
            "intent": {"action": "query", "scope": "genai.policy"},
        }

    def test_create_task(self, task_tracker, sample_task_data):
        """測試 create_task() 方法：創建任務記錄"""
        task_id = task_tracker.create_task(**sample_task_data)

        assert task_id is not None
        assert isinstance(task_id, str)
        assert len(task_id) > 0

        # 驗證任務已創建
        task_record = task_tracker.get_task_status(task_id)
        assert task_record is not None
        assert task_record.instruction == sample_task_data["instruction"]
        assert task_record.target_agent_id == sample_task_data["target_agent_id"]
        assert task_record.user_id == sample_task_data["user_id"]
        assert task_record.status == TaskStatus.PENDING

    def test_get_task_status(self, task_tracker, sample_task_data):
        """測試 get_task_status() 方法：查詢任務狀態"""
        task_id = task_tracker.create_task(**sample_task_data)

        task_record = task_tracker.get_task_status(task_id)

        assert task_record is not None
        assert task_record.task_id == task_id
        assert task_record.instruction == sample_task_data["instruction"]

    def test_get_task_status_not_found(self, task_tracker):
        """測試 get_task_status() 方法：任務不存在時返回 None"""
        task_record = task_tracker.get_task_status("nonexistent_task_id")

        assert task_record is None

    def test_update_task_status(self, task_tracker, sample_task_data):
        """測試 update_task_status() 方法：更新任務狀態"""
        task_id = task_tracker.create_task(**sample_task_data)

        # 更新狀態為 running
        success = task_tracker.update_task_status(task_id=task_id, status=TaskStatus.RUNNING)

        assert success is True

        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.RUNNING

    def test_update_task_status_with_result(self, task_tracker, sample_task_data):
        """測試 update_task_status() 方法：更新任務狀態和結果"""
        task_id = task_tracker.create_task(**sample_task_data)

        result = {"config": {"max_concurrent_requests": 100}}
        success = task_tracker.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result=result,
        )

        assert success is True

        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.COMPLETED
        assert task_record.result == result

    def test_update_task_status_with_error(self, task_tracker, sample_task_data):
        """測試 update_task_status() 方法：更新任務狀態和錯誤信息"""
        task_id = task_tracker.create_task(**sample_task_data)

        error = "配置定義未找到"
        success = task_tracker.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            error=error,
        )

        assert success is True

        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.FAILED
        assert task_record.error == error

    def test_update_task_status_not_found(self, task_tracker):
        """測試 update_task_status() 方法：任務不存在時返回 False"""
        success = task_tracker.update_task_status(
            task_id="nonexistent_task_id",
            status=TaskStatus.COMPLETED,
        )

        assert success is False

    def test_task_status_flow(self, task_tracker, sample_task_data):
        """測試任務狀態流轉：pending → running → completed"""
        task_id = task_tracker.create_task(**sample_task_data)

        # 初始狀態為 PENDING
        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.PENDING

        # 更新為 RUNNING
        task_tracker.update_task_status(task_id=task_id, status=TaskStatus.RUNNING)
        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.RUNNING

        # 更新為 COMPLETED
        task_tracker.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            result={"success": True},
        )
        task_record = task_tracker.get_task_status(task_id)
        assert task_record.status == TaskStatus.COMPLETED

    def test_list_tasks_by_user(self, task_tracker):
        """測試 list_tasks() 方法：按用戶查詢任務"""
        # 創建用戶 A 的任務
        task_id_a1 = task_tracker.create_task(
            instruction="任務 A1",
            target_agent_id="agent1",
            user_id="user_a",
        )
        task_id_a2 = task_tracker.create_task(
            instruction="任務 A2",
            target_agent_id="agent1",
            user_id="user_a",
        )

        # 創建用戶 B 的任務
        task_id_b1 = task_tracker.create_task(
            instruction="任務 B1",
            target_agent_id="agent1",
            user_id="user_b",
        )

        # 查詢用戶 A 的任務
        user_a_tasks = task_tracker.list_tasks(user_id="user_a")

        assert len(user_a_tasks) == 2
        task_ids = [task.task_id for task in user_a_tasks]
        assert task_id_a1 in task_ids
        assert task_id_a2 in task_ids
        assert task_id_b1 not in task_ids

    def test_list_tasks_by_status(self, task_tracker, sample_task_data):
        """測試 list_tasks() 方法：按狀態查詢任務"""
        # 創建多個任務並設置不同狀態
        task_id_1 = task_tracker.create_task(**sample_task_data)
        task_id_2 = task_tracker.create_task(**sample_task_data)
        task_tracker.create_task(**sample_task_data)  # task_id_3 保持 PENDING

        task_tracker.update_task_status(task_id_1, TaskStatus.COMPLETED)
        task_tracker.update_task_status(task_id_2, TaskStatus.FAILED)

        # 查詢 COMPLETED 狀態的任務
        completed_tasks = task_tracker.list_tasks(status=TaskStatus.COMPLETED)

        assert len(completed_tasks) == 1
        assert completed_tasks[0].task_id == task_id_1

    def test_list_tasks_limit(self, task_tracker, sample_task_data):
        """測試 list_tasks() 方法：限制返回數量"""
        # 創建多個任務
        for i in range(10):
            task_tracker.create_task(
                instruction=f"任務 {i}",
                target_agent_id="agent1",
                user_id="user_123",
            )

        # 查詢並限制返回 5 條
        tasks = task_tracker.list_tasks(limit=5)

        assert len(tasks) == 5

    def test_list_tasks_sorted_by_time(self, task_tracker, sample_task_data):
        """測試 list_tasks() 方法：按創建時間倒序排序"""
        # 創建多個任務
        task_ids = []
        for i in range(5):
            task_id = task_tracker.create_task(
                instruction=f"任務 {i}",
                target_agent_id="agent1",
                user_id="user_123",
            )
            task_ids.append(task_id)

        # 查詢任務（應該按創建時間倒序）
        tasks = task_tracker.list_tasks()

        # 驗證順序（最新的在前）
        for i in range(len(tasks) - 1):
            assert tasks[i].created_at >= tasks[i + 1].created_at

    def test_get_tasks_by_user(self, task_tracker):
        """測試 get_tasks_by_user() 方法：獲取用戶的所有任務"""
        # 創建用戶 A 的任務
        task_tracker.create_task(
            instruction="任務 A1",
            target_agent_id="agent1",
            user_id="user_a",
        )
        task_tracker.create_task(
            instruction="任務 A2",
            target_agent_id="agent1",
            user_id="user_a",
        )

        # 創建用戶 B 的任務
        task_tracker.create_task(
            instruction="任務 B1",
            target_agent_id="agent1",
            user_id="user_b",
        )

        # 查詢用戶 A 的任務
        user_a_tasks = task_tracker.get_tasks_by_user("user_a")

        assert len(user_a_tasks) == 2
        for task in user_a_tasks:
            assert task.user_id == "user_a"

    def test_task_record_to_dict(self, sample_task_data):
        """測試 TaskRecord.to_dict() 方法：轉換為字典"""
        task_record = TaskRecord(
            task_id="test_task_123",
            instruction=sample_task_data["instruction"],
            target_agent_id=sample_task_data["target_agent_id"],
            user_id=sample_task_data["user_id"],
            intent=sample_task_data["intent"],
            status=TaskStatus.PENDING,
        )

        task_dict = task_record.to_dict()

        assert isinstance(task_dict, dict)
        assert task_dict["task_id"] == "test_task_123"
        assert task_dict["instruction"] == sample_task_data["instruction"]
        assert task_dict["target_agent_id"] == sample_task_data["target_agent_id"]
        assert task_dict["user_id"] == sample_task_data["user_id"]
        assert task_dict["status"] == TaskStatus.PENDING.value
        assert "created_at" in task_dict
        assert "updated_at" in task_dict
