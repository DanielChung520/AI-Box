#!/usr/bin/env python3
# 代碼功能說明: 測試 DateTimeTool 意圖識別和執行流程
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""測試 DateTimeTool 意圖識別和執行流程

直接測試 Task Analyzer 如何處理時間查詢，並模擬完整的執行流程。
"""

import asyncio
import sys
from pathlib import Path

# 添加項目根目錄到 Python 路徑
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.task_analyzer.analyzer import TaskAnalyzer
from agents.task_analyzer.models import TaskAnalysisRequest


async def test_datetime_query():
    """測試時間查詢的完整流程"""
    print("=" * 80)
    print("測試：告訴我此刻時間")
    print("=" * 80)

    # 創建 Task Analyzer
    analyzer = TaskAnalyzer()

    # 準備請求
    request = TaskAnalysisRequest(
        task="告訴我此刻時間",
        context={
            "user_id": "test_user",
            "session_id": "test_session",
            "request_id": "test_request",
        },
        user_id="test_user",
        session_id="test_session",
    )

    print(f"\n📝 用戶查詢: {request.task}")
    print(f"📝 用戶 ID: {request.user_id}")
    print(f"📝 Session ID: {request.session_id}")

    try:
        # 執行分析
        print("\n🔍 開始執行 Task Analyzer...")
        result = await analyzer.analyze(request)

        print("\n✅ Task Analyzer 執行成功!")
        print(f"📋 Task ID: {result.task_id}")
        print(f"📋 Task Type: {result.task_type}")
        print(f"📋 Workflow Type: {result.workflow_type}")
        print(f"📋 LLM Provider: {result.llm_provider}")
        print(f"📋 Confidence: {result.confidence}")

        # 檢查 Router Decision
        print("\n" + "=" * 80)
        print("📊 Router Decision 分析結果")
        print("=" * 80)
        if result.router_decision:
            rd = result.router_decision
            print(f"  Intent Type: {rd.intent_type}")
            print(f"  Complexity: {rd.complexity}")
            print(f"  Needs Agent: {rd.needs_agent}")
            print(f"  Needs Tools: {rd.needs_tools}")
            print(f"  Determinism Required: {rd.determinism_required}")
            print(f"  Risk Level: {rd.risk_level}")
            print(f"  Confidence: {rd.confidence}")
        else:
            print("  ⚠️  Router Decision 為 None")

        # 檢查 Decision Result
        print("\n" + "=" * 80)
        print("🎯 Decision Result 分析結果")
        print("=" * 80)
        if result.decision_result:
            dr = result.decision_result
            print(f"  Chosen Agent: {dr.chosen_agent}")
            print(f"  Chosen Tools: {dr.chosen_tools}")
            print(f"  Chosen Model: {dr.chosen_model}")
            print(f"  Score: {dr.score}")
            print(f"  Fallback Used: {dr.fallback_used}")
            print(f"  Reasoning: {dr.reasoning}")

            # 檢查是否選擇了工具
            if dr.chosen_tools:
                print(f"\n  ✅ 選擇了 {len(dr.chosen_tools)} 個工具:")
                for tool in dr.chosen_tools:
                    print(f"    - {tool}")

                # 檢查是否包含 datetime 工具
                if "datetime" in dr.chosen_tools:
                    print("\n  ✅ 包含 datetime 工具，可以執行時間查詢")
                else:
                    print("\n  ⚠️  未包含 datetime 工具")
            else:
                print("\n  ⚠️  未選擇任何工具")
        else:
            print("  ⚠️  Decision Result 為 None")

        # 檢查 Analysis Details
        print("\n" + "=" * 80)
        print("📄 Analysis Details")
        print("=" * 80)
        if result.analysis_details:
            print(f"  Direct Answer: {result.analysis_details.get('direct_answer', False)}")
            if result.analysis_details.get("direct_answer"):
                print(f"  Response: {result.analysis_details.get('response', 'N/A')[:200]}")

        # 模擬工具執行
        print("\n" + "=" * 80)
        print("🔧 模擬工具執行")
        print("=" * 80)
        if result.decision_result and result.decision_result.chosen_tools:
            if "datetime" in result.decision_result.chosen_tools:
                print("  嘗試執行 DateTimeTool...")
                try:
                    from tools.time import DateTimeInput, DateTimeTool

                    datetime_tool = DateTimeTool()
                    datetime_input = DateTimeInput(
                        tenant_id=None,
                        user_id="test_user",
                    )
                    tool_result = await datetime_tool.execute(datetime_input)

                    print("  ✅ DateTimeTool 執行成功!")
                    print(f"  📅 時間: {tool_result.datetime}")
                    if hasattr(tool_result, "timezone"):
                        print(f"  🌍 時區: {tool_result.timezone}")

                    # 格式化結果
                    time_response = f"現在的時間是：{tool_result.datetime}"
                    if hasattr(tool_result, "timezone"):
                        time_response += f"（時區：{tool_result.timezone}）"
                    print(f"\n  💬 格式化後的響應: {time_response}")
                except Exception as e:
                    print(f"  ❌ DateTimeTool 執行失敗: {e}")
                    import traceback

                    traceback.print_exc()
            else:
                print("  ⚠️  未選擇 datetime 工具，跳過執行")
        else:
            print("  ⚠️  未選擇工具，無法執行")

        # 總結
        print("\n" + "=" * 80)
        print("📊 測試總結")
        print("=" * 80)
        if result.decision_result and result.decision_result.chosen_tools:
            if "datetime" in result.decision_result.chosen_tools:
                print("✅ 測試通過：Task Analyzer 正確識別了時間查詢並選擇了 datetime 工具")
            else:
                print("⚠️  測試部分通過：Task Analyzer 選擇了工具，但未包含 datetime 工具")
                print(f"   選擇的工具: {result.decision_result.chosen_tools}")
        else:
            print("❌ 測試失敗：Task Analyzer 未選擇任何工具")
            if result.router_decision:
                print(f"   Router Decision - needs_tools: {result.router_decision.needs_tools}")

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


async def test_simple_query():
    """測試簡單查詢（對比測試）"""
    print("\n\n" + "=" * 80)
    print("對比測試：簡單查詢（你好）")
    print("=" * 80)

    analyzer = TaskAnalyzer()
    request = TaskAnalysisRequest(
        task="你好",
        context={
            "user_id": "test_user",
            "session_id": "test_session",
        },
        user_id="test_user",
        session_id="test_session",
    )

    try:
        result = await analyzer.analyze(request)
        print(f"\n📝 查詢: {request.task}")
        if result.decision_result:
            print(f"📊 Chosen Tools: {result.decision_result.chosen_tools}")
            print(
                f"📊 Needs Tools (Router): {result.router_decision.needs_tools if result.router_decision else 'N/A'}"
            )
        print("✅ 簡單查詢測試完成")
    except Exception as e:
        print(f"❌ 簡單查詢測試失敗: {e}")


if __name__ == "__main__":
    print("\n🚀 開始測試 DateTimeTool 意圖識別和執行流程\n")

    # 測試時間查詢
    success = asyncio.run(test_datetime_query())

    # 對比測試（簡單查詢）
    asyncio.run(test_simple_query())

    print("\n" + "=" * 80)
    if success:
        print("✅ 所有測試完成")
    else:
        print("❌ 部分測試失敗，請檢查輸出")
    print("=" * 80 + "\n")
