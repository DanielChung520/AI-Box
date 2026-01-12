# 代碼功能說明: md-editor 場景調試測試腳本
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""md-editor 場景調試測試腳本

專門用於調試 md-editor Agent 調用問題的測試腳本。
只測試 md-editor 場景（20 個場景），並添加詳細日誌以追蹤 Agent 匹配和選擇過程。

測試目標：
1. 確認 CapabilityMatcher 是否找到了 md-editor agent
2. 確認 DecisionEngine 是否選擇了 md-editor
3. 確認 _select_agent_by_file_extension 是否正確匹配 .md 文件
4. 找出 Agent 調用失敗的根本原因
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from agents.services.orchestrator.orchestrator import AgentOrchestrator
from agents.task_analyzer.models import TaskAnalysisRequest

# 設置詳細日誌
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Agent ID 定義
MD_EDITOR_AGENT_ID = "md-editor"

# md-editor 測試場景（20 個場景）
MD_EDITOR_SCENARIOS = [
    {
        "scenario_id": "MD-001",
        "category": "md-editor",
        "user_input": "編輯文件 README.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-002",
        "category": "md-editor",
        "user_input": "修改 docs/guide.md 文件中的第一章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-003",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝說明",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-004",
        "category": "md-editor",
        "user_input": "更新 CHANGELOG.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-005",
        "category": "md-editor",
        "user_input": "刪除 docs/api.md 中的過時文檔",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-006",
        "category": "md-editor",
        "user_input": "將 README.md 中的 '舊版本' 替換為 '新版本'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-007",
        "category": "md-editor",
        "user_input": "重寫 docs/guide.md 中的使用說明章節",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-008",
        "category": "md-editor",
        "user_input": "在 README.md 的開頭插入版本信息",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-009",
        "category": "md-editor",
        "user_input": "格式化整個 README.md 文件",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-010",
        "category": "md-editor",
        "user_input": "整理 docs/guide.md 的章節結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-011",
        "category": "md-editor",
        "user_input": "創建一個新的 Markdown 文件 CONTRIBUTING.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-012",
        "category": "md-editor",
        "user_input": "幫我產生一份 API 文檔 api.md",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-013",
        "category": "md-editor",
        "user_input": "在 README.md 中添加功能對照表",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-014",
        "category": "md-editor",
        "user_input": "更新 docs/links.md 中的所有外部鏈接",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-015",
        "category": "md-editor",
        "user_input": "在 README.md 中添加安裝代碼示例",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-016",
        "category": "md-editor",
        "user_input": "將 docs/guide.md 的主標題改為 '用戶指南'",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-017",
        "category": "md-editor",
        "user_input": "在 README.md 中添加項目截圖",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
    {
        "scenario_id": "MD-018",
        "category": "md-editor",
        "user_input": "優化 docs/api.md 的 Markdown 格式",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-019",
        "category": "md-editor",
        "user_input": "在 README.md 開頭添加目錄",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "簡單",
    },
    {
        "scenario_id": "MD-020",
        "category": "md-editor",
        "user_input": "重組 docs/guide.md 的內容結構",
        "expected_task_type": "execution",
        "expected_agent": MD_EDITOR_AGENT_ID,
        "complexity": "中等",
    },
]


async def run_single_test(scenario: Dict[str, Any]) -> Dict[str, Any]:
    """
    執行單個測試場景

    Args:
        scenario: 測試場景定義

    Returns:
        測試結果
    """
    scenario_id = scenario["scenario_id"]
    user_input = scenario["user_input"]
    expected_task_type = scenario["expected_task_type"]
    expected_agent = scenario["expected_agent"]

    logger.info(f"\n{'='*80}")
    logger.info(f"測試場景: {scenario_id}")
    logger.info(f"用戶輸入: {user_input}")
    logger.info(f"預期任務類型: {expected_task_type}")
    logger.info(f"預期 Agent: {expected_agent}")
    logger.info(f"{'='*80}\n")

    try:
        # 確保 builtin agents 已註冊
        try:
            from agents.builtin import register_builtin_agents

            register_builtin_agents()
            logger.info("Builtin agents registered successfully")
        except Exception as e:
            logger.warning(f"Agent registration failed: {e}")

        # 初始化 Orchestrator 和 TaskAnalyzer
        orchestrator = AgentOrchestrator()
        task_analyzer = orchestrator.task_analyzer

        # 創建分析請求
        analysis_request = TaskAnalysisRequest(
            task=user_input,
            context={"user_id": "test_user", "task": user_input, "query": user_input},
        )

        logger.info("開始任務分析...")
        analysis_result = await task_analyzer.analyze(analysis_request)

        # 提取結果
        actual_task_type = analysis_result.task_type.value if analysis_result.task_type else None
        actual_intent_type = (
            analysis_result.router_decision.intent_type.value
            if analysis_result.router_decision
            else None
        )
        actual_agents = (
            [agent.agent_id for agent in analysis_result.selected_agents]
            if analysis_result.selected_agents
            else []
        )

        # 驗證結果
        task_type_match = actual_task_type == expected_task_type
        agent_match = expected_agent in actual_agents if actual_agents else False
        all_passed = task_type_match and agent_match

        # 記錄詳細結果
        logger.info("\n測試結果:")
        logger.info(
            f"  任務類型: {actual_task_type} (預期: {expected_task_type}) {'✅' if task_type_match else '❌'}"
        )
        logger.info(f"  意圖類型: {actual_intent_type}")
        logger.info(f"  實際 Agent: {actual_agents}")
        logger.info(f"  預期 Agent: {expected_agent}")
        logger.info(f"  Agent 匹配: {'✅' if agent_match else '❌'}")
        logger.info(f"  整體通過: {'✅' if all_passed else '❌'}")

        # 檢查 agent_candidates（從日誌中提取，如果可能）
        if not actual_agents:
            logger.warning("⚠️  沒有調用到任何 Agent！")
            logger.warning("   需要檢查 CapabilityMatcher 是否找到了 md-editor")
            logger.warning("   需要檢查 DecisionEngine 是否選擇了 md-editor")

        return {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "complexity": scenario["complexity"],
            "user_input": user_input,
            "expected_task_type": expected_task_type,
            "expected_agent": expected_agent,
            "actual_task_type": actual_task_type,
            "actual_intent_type": actual_intent_type,
            "actual_agents": actual_agents,
            "task_type_match": task_type_match,
            "agent_match": agent_match,
            "all_passed": all_passed,
            "status": "✅ 通過" if all_passed else "❌ 失敗",
        }

    except Exception as e:
        logger.error(f"測試場景 {scenario_id} 執行失敗: {e}", exc_info=True)
        return {
            "scenario_id": scenario_id,
            "category": scenario["category"],
            "user_input": user_input,
            "expected_task_type": expected_task_type,
            "expected_agent": expected_agent,
            "error": str(e),
            "status": "❌ 錯誤",
            "all_passed": False,
        }


async def run_all_tests() -> None:
    """執行所有 md-editor 場景測試"""
    logger.info("=" * 80)
    logger.info("開始 md-editor 場景調試測試")
    logger.info(f"總場景數: {len(MD_EDITOR_SCENARIOS)}")
    logger.info("=" * 80)

    results = []
    for scenario in MD_EDITOR_SCENARIOS:
        result = await run_single_test(scenario)
        results.append(result)

    # 統計結果
    total = len(results)
    passed = sum(1 for r in results if r.get("all_passed", False))
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0

    logger.info("\n" + "=" * 80)
    logger.info("測試結果統計")
    logger.info("=" * 80)
    logger.info(f"總場景數: {total}")
    logger.info(f"通過: {passed}")
    logger.info(f"失敗: {failed}")
    logger.info(f"通過率: {pass_rate:.2f}%")

    # Agent 調用統計
    agents_with_agents = sum(1 for r in results if r.get("actual_agents", []))
    logger.info("\nAgent 調用統計:")
    logger.info(
        f"  有 Agent 的場景: {agents_with_agents} / {total} ({agents_with_agents/total*100:.1f}%)"
    )
    logger.info(
        f"  無 Agent 的場景: {total - agents_with_agents} / {total} ({(total-agents_with_agents)/total*100:.1f}%)"
    )

    # 任務類型統計
    task_type_correct = sum(
        1 for r in results if r.get("actual_task_type") == r.get("expected_task_type")
    )
    logger.info("\n任務類型識別:")
    logger.info(f"  正確: {task_type_correct} / {total} ({task_type_correct/total*100:.1f}%)")

    # 保存結果到文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = Path(f"tests/agents/test_reports/md_editor_debug_{timestamp}.json")
    report_file.parent.mkdir(parents=True, exist_ok=True)

    report_data = {
        "test_type": "md-editor_debug",
        "timestamp": timestamp,
        "total_scenarios": total,
        "passed": passed,
        "failed": failed,
        "pass_rate": pass_rate,
        "results": results,
    }

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n測試報告已保存到: {report_file}")

    # 打印失敗場景
    failed_scenarios = [r for r in results if not r.get("all_passed", False)]
    if failed_scenarios:
        logger.info(f"\n失敗場景 ({len(failed_scenarios)} 個):")
        for r in failed_scenarios:
            logger.info(
                f"  {r['scenario_id']}: {r['user_input'][:50]}... -> "
                f"agents={r.get('actual_agents', [])}, expected={r.get('expected_agent')}"
            )


if __name__ == "__main__":
    # 設置環境變量（如果需要）
    import os

    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = str(_project_root)

    # 運行測試
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        logger.info("\n測試被用戶中斷")
    except Exception as e:
        logger.error(f"測試執行失敗: {e}", exc_info=True)
