# 代碼功能說明: Policy 引擎性能測試
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""Policy 引擎性能測試 - 測試規則引擎執行時間"""

import statistics
import time
from typing import List

import pytest

from agents.task_analyzer.models import PolicyRule, TaskDAG, TaskNode
from agents.task_analyzer.policy_service import PolicyService


class TestPolicyPerformance:
    """Policy 引擎性能測試類"""

    @pytest.fixture
    def policy_service(self):
        """創建 Policy Service 實例"""
        return PolicyService()

    @pytest.fixture
    def sample_task_dag(self):
        """創建示例 Task DAG"""
        return TaskDAG(
            task_graph=[
                TaskNode(
                    id="T1",
                    capability="query",
                    agent="data_agent",
                    depends_on=[],
                ),
                TaskNode(
                    id="T2",
                    capability="process",
                    agent="data_agent",
                    depends_on=["T1"],
                ),
            ],
            reasoning="測試任務",
        )

    @pytest.mark.asyncio
    async def test_policy_check_time(
        self, policy_service: PolicyService, sample_task_dag: TaskDAG
    ):
        """測試 Policy 檢查時間"""
        context = {
            "task_dag": sample_task_dag,
            "user_id": "test_user",
            "tenant_id": "test_tenant",
        }

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            result = await policy_service.validate_task(
                task_dag=sample_task_dag,
                user_id="test_user",
                tenant_id="test_tenant",
            )
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)
            assert result is not None

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"Policy 檢查響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # 驗證 P95 響應時間 ≤100ms
        assert p95_time <= 0.1, f"Policy 檢查 P95 響應時間 {p95_time:.3f}s 超過 100ms"

    @pytest.mark.asyncio
    async def test_rule_evaluation_performance(
        self, policy_service: PolicyService
    ):
        """測試規則評估性能"""
        # 添加多個規則
        for i in range(10):
            rule = PolicyRule(
                rule_id=f"test_rule_{i}",
                rule_type="risk",
                conditions={"task_count": {"operator": ">", "value": i}},
                action="allow",
            )
            policy_service.add_rule(rule)

        context = {"task_count": 5}

        response_times: List[float] = []

        for _ in range(10):
            start_time = time.time()
            result = policy_service.evaluate_rules(context)
            elapsed_time = time.time() - start_time
            response_times.append(elapsed_time)

        mean_time = statistics.mean(response_times)
        p95_time = statistics.quantiles(response_times, n=20)[18]

        print(f"規則評估響應時間統計:")
        print(f"  平均: {mean_time:.3f}s")
        print(f"  P95: {p95_time:.3f}s")

        # 規則評估應該很快
        assert p95_time <= 0.05, f"規則評估 P95 響應時間 {p95_time:.3f}s 超過 50ms"
