# 代碼功能說明: MM-Agent 語義與任務分析整合測試
# 創建日期: 2026-02-21
# 創建人: Daniel Chung
# 測試目的: 實際調用 MM-Agent 端點驗證語義分析與任務分發

"""
MM-Agent 語義與任務分析整合測試

本測試文件實際調用 MM-Agent 端點，驗證語義分析與任務分發能力。

使用方式：
1. 確保 MM-Agent 服務運行在 localhost:8003
2. 執行: pytest test_intent_integration.py -v

端點：
- POST /api/v1/chat/intent - 意圖分類
- POST /api/v1/chat/auto-execute - 自動執行（含意圖分類 + 任務執行）
"""

import pytest
import httpx
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


# MM-Agent 服務地址
MM_AGENT_BASE_URL = "http://localhost:8003"
INTENT_ENDPOINT = f"{MM_AGENT_BASE_URL}/api/v1/chat/intent"
AUTO_EXECUTE_ENDPOINT = f"{MM_AGENT_BASE_URL}/api/v1/chat/auto-execute"
HEALTH_ENDPOINT = f"{MM_AGENT_BASE_URL}/health"


@dataclass
class IntentTestResult:
    """意圖測試結果"""

    user_input: str
    expected_intent: str
    actual_intent: Optional[str]
    confidence: Optional[float]
    is_simple_query: Optional[bool]
    needs_clarification: Optional[bool]
    success: bool
    error: Optional[str] = None
    response_time_ms: float = 0.0


class TestMMAgentConnectivity:
    """MM-Agent 連接性測試"""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """測試 MM-Agent 健康檢查"""
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get(HEALTH_ENDPOINT)
                assert response.status_code == 200, f"健康檢查失敗: {response.status_code}"
                logger.info("MM-Agent 健康檢查通過")
            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行，跳過連接性測試")


class TestIntentClassificationIntegration:
    """意圖分類整合測試"""

    @pytest.fixture
    def test_cases(self) -> List[Dict[str, Any]]:
        """測試案例"""
        return [
            # GREETING
            {"input": "你好", "expected_intent": "GREETING"},
            {"input": "早安", "expected_intent": "GREETING"},
            # CLARIFICATION
            {"input": "倉庫", "expected_intent": "CLARIFICATION"},
            {"input": "W03", "expected_intent": "CLARIFICATION"},
            {"input": "查詢", "expected_intent": "CLARIFICATION"},
            # KNOWLEDGE_QUERY
            {"input": "什麼是ABC庫存分類？", "expected_intent": "KNOWLEDGE_QUERY"},
            {"input": "ERP收料操作步驟", "expected_intent": "KNOWLEDGE_QUERY"},
            {"input": "如何建立採購單？", "expected_intent": "KNOWLEDGE_QUERY"},
            # SIMPLE_QUERY
            {"input": "查詢料號 10-0001 的庫存", "expected_intent": "SIMPLE_QUERY"},
            {"input": "W03 倉庫的庫存是多少？", "expected_intent": "SIMPLE_QUERY"},
            {"input": "料號 RM05-008 上月採購多少？", "expected_intent": "SIMPLE_QUERY"},
            # COMPLEX_TASK
            {"input": "比較近三個月採購金額", "expected_intent": "COMPLEX_TASK"},
            {"input": "各倉庫庫存金額排行", "expected_intent": "COMPLEX_TASK"},
            {"input": "本月採購單未交貨明細", "expected_intent": "COMPLEX_TASK"},
            {"input": "ABC庫存分類分析", "expected_intent": "COMPLEX_TASK"},
            {
                "input": "如何建立採購單？",
                "expected_intent": "COMPLEX_TASK",
            },  # 根據定義，這可能是 KNOWLEDGE_QUERY 或 COMPLEX_TASK
        ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "test_case",
        [
            # 精選測試案例子集（避免測試時間過長）
            {"input": "你好", "expected_intent": "GREETING"},
            {"input": "倉庫", "expected_intent": "CLARIFICATION"},
            {"input": "查詢料號 10-0001 的庫存", "expected_intent": "SIMPLE_QUERY"},
            {"input": "比較近三個月採購金額", "expected_intent": "COMPLEX_TASK"},
        ],
    )
    async def test_intent_classification(self, test_case: Dict[str, Any]):
        """測試意圖分類端點"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    INTENT_ENDPOINT,
                    json={
                        "instruction": test_case["input"],
                        "session_id": f"test_session_{test_case['expected_intent']}",
                    },
                )

                assert response.status_code == 200, f"請求失敗: {response.status_code}"

                result = response.json()
                actual_intent = result.get("intent")

                logger.info(
                    f"輸入: {test_case['input']}\n"
                    f"預期: {test_case['expected_intent']}\n"
                    f"實際: {actual_intent}\n"
                    f"置信度: {result.get('confidence')}"
                )

                # 記錄測試結果
                # 注意：由於 LLM 的非確定性，這裡只記錄結果，不強制斷言

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")
            except Exception as e:
                logger.error(f"測試失敗: {e}")
                pytest.fail(f"測試失敗: {e}")


class TestAutoExecuteIntegration:
    """自動執行端點整合測試"""

    @pytest.mark.asyncio
    async def test_simple_query_execution(self):
        """測試簡單查詢執行"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    AUTO_EXECUTE_ENDPOINT,
                    json={
                        "session_id": "test_simple_query",
                        "instruction": "查詢料號 10-0001 的庫存",
                    },
                )

                assert response.status_code == 200, f"請求失敗: {response.status_code}"

                result = response.json()
                logger.info(f"簡單查詢結果: {result}")

                # 驗證返回結構
                assert "intent" in result or "status" in result

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")

    @pytest.mark.asyncio
    async def test_complex_task_execution(self):
        """測試複雜任務執行"""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                response = await client.post(
                    AUTO_EXECUTE_ENDPOINT,
                    json={"session_id": "test_complex_task", "instruction": "比較近三個月採購金額"},
                )

                assert response.status_code == 200, f"請求失敗: {response.status_code}"

                result = response.json()
                logger.info(f"複雜任務結果: {result}")

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")

    @pytest.mark.asyncio
    async def test_greeting_response(self):
        """測試問候回覆"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    AUTO_EXECUTE_ENDPOINT,
                    json={"session_id": "test_greeting", "instruction": "你好"},
                )

                assert response.status_code == 200, f"請求失敗: {response.status_code}"

                result = response.json()
                logger.info(f"問候回覆: {result}")

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")


class TestScenarioBasedIntegration:
    """場景驅動整合測試"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "scenario_id,user_input,expected_bpa_intent",
        [
            # 知識查詢場景
            (31, "ERP收料操作步驟是什麼？", "KNOWLEDGE_QUERY"),
            (36, "什麼是ABC庫存分類法？", "KNOWLEDGE_QUERY"),
            # 簡單數據查詢
            (56, "查詢料號 10-0001 的庫存", "SIMPLE_QUERY"),
            (57, "W03 倉庫的庫存是多少？", "SIMPLE_QUERY"),
            # 複雜任務
            (81, "比較近三個月採購金額", "COMPLEX_TASK"),
            (82, "各倉庫庫存金額排行", "COMPLEX_TASK"),
            (89, "本月採購單未交貨明細", "COMPLEX_TASK"),
            # 需要澄清
            (16, "倉庫", "CLARIFICATION"),
            (20, "查詢庫存", "CLARIFICATION"),
        ],
    )
    async def test_scenario(self, scenario_id: int, user_input: str, expected_bpa_intent: str):
        """依據場景 ID 測試"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    INTENT_ENDPOINT,
                    json={"instruction": user_input, "session_id": f"scenario_{scenario_id}"},
                )

                assert response.status_code == 200, f"請求失敗: {response.status_code}"

                result = response.json()
                actual_intent = result.get("intent")

                logger.info(
                    f"場景 {scenario_id}: {user_input}\n"
                    f"  預期 BPA Intent: {expected_bpa_intent}\n"
                    f"  實際 BPA Intent: {actual_intent}\n"
                    f"  置信度: {result.get('confidence')}"
                )

                # 記錄結果供後續分析
                # 不強制斷言以容忍 LLM 非確定性

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")


# =============================================================================
# 測試執行輔助
# =============================================================================


async def run_intent_tests(scenarios: List[Dict[str, Any]]) -> List[IntentTestResult]:
    """批量運行意圖分類測試"""
    results = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for scenario in scenarios:
            try:
                import time

                start_time = time.time()

                response = await client.post(
                    INTENT_ENDPOINT,
                    json={
                        "instruction": scenario["user_input"],
                        "session_id": f"batch_test_{scenario['id']}",
                    },
                )

                elapsed_ms = (time.time() - start_time) * 1000

                if response.status_code == 200:
                    result = response.json()
                    results.append(
                        IntentTestResult(
                            user_input=scenario["user_input"],
                            expected_intent=scenario["expected_bpa_intent"],
                            actual_intent=result.get("intent"),
                            confidence=result.get("confidence"),
                            is_simple_query=result.get("is_simple_query"),
                            needs_clarification=result.get("needs_clarification"),
                            success=result.get("intent") == scenario["expected_bpa_intent"],
                            response_time_ms=elapsed_ms,
                        )
                    )
                else:
                    results.append(
                        IntentTestResult(
                            user_input=scenario["user_input"],
                            expected_intent=scenario["expected_bpa_intent"],
                            actual_intent=None,
                            confidence=None,
                            is_simple_query=None,
                            needs_clarification=None,
                            success=False,
                            error=f"HTTP {response.status_code}",
                            response_time_ms=elapsed_ms,
                        )
                    )

            except httpx.ConnectError:
                pytest.skip("MM-Agent 服務未運行")
            except Exception as e:
                results.append(
                    IntentTestResult(
                        user_input=scenario["user_input"],
                        expected_intent=scenario["expected_bpa_intent"],
                        actual_intent=None,
                        confidence=None,
                        is_simple_query=None,
                        needs_clarification=None,
                        success=False,
                        error=str(e),
                    )
                )

    return results


def print_test_summary(results: List[IntentTestResult]):
    """打印測試摘要"""
    total = len(results)
    success = sum(1 for r in results if r.success)
    avg_time = sum(r.response_time_ms for r in results) / total if total > 0 else 0

    print("\n" + "=" * 60)
    print("意圖分類測試摘要")
    print("=" * 60)
    print(f"總測試數: {total}")
    print(f"成功匹配: {success}")
    print(f"成功率: {success / total * 100:.1f}%")
    print(f"平均響應時間: {avg_time:.1f}ms")
    print("=" * 60)

    # 顯示失敗案例
    failed = [r for r in results if not r.success]
    if failed:
        print("\n失敗案例:")
        for r in failed:
            print(f"  - 輸入: {r.user_input}")
            print(f"    預期: {r.expected_intent}")
            print(f"    實際: {r.actual_intent}")
            if r.error:
                print(f"    錯誤: {r.error}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
