#!/usr/bin/env python3
# 代碼功能說明: 分析模型比較測試結果
# 創建日期: 2026-01-09
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-09

"""分析模型比較測試結果，找出最適合意圖判斷的模型"""

import json
from pathlib import Path
from typing import Any, Dict


def analyze_json_report(json_file: Path) -> Dict[str, Any]:
    """分析 JSON 報告文件"""
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    data.get("results", [])
    statistics = data.get("statistics", {})

    # 計算每個模型的綜合評分
    model_scores = {}

    for model_name, stats in statistics.items():
        # 綜合評分 = 任務類型識別正確率 * 0.4 + needs_agent 正確率 * 0.3 + 整體成功率 * 0.3
        # 但需要考慮耗時（耗時越短越好）
        task_type_acc = stats.get("task_type_accuracy", 0)
        needs_agent_acc = stats.get("needs_agent_accuracy", 0)
        overall_acc = stats.get("overall_success_rate", 0)
        avg_time = stats.get("avg_time", 0)

        # 基礎分數（正確率）
        base_score = (task_type_acc * 0.4 + needs_agent_acc * 0.3 + overall_acc * 0.3) / 100

        # 速度加分（假設 5 秒為基準，越快越好）
        speed_bonus = max(0, (5 - avg_time) / 5 * 0.1) if avg_time > 0 else 0

        # 綜合評分
        final_score = base_score + speed_bonus

        model_scores[model_name] = {
            "task_type_accuracy": task_type_acc,
            "needs_agent_accuracy": needs_agent_acc,
            "overall_success_rate": overall_acc,
            "avg_time": avg_time,
            "score": final_score,
        }

    # 按評分排序
    sorted_models = sorted(model_scores.items(), key=lambda x: x[1]["score"], reverse=True)

    return {
        "model_scores": model_scores,
        "sorted_models": sorted_models,
        "best_model": sorted_models[0][0] if sorted_models else None,
        "statistics": statistics,
    }


def print_analysis(analysis: Dict[str, Any]):
    """打印分析結果"""
    print("=" * 80)
    print("模型比較分析結果")
    print("=" * 80)

    sorted_models = analysis["sorted_models"]
    best_model = analysis["best_model"]

    print("\n📊 模型排名（按綜合評分）：")
    print("-" * 80)
    print(
        f"{'排名':<6} {'模型名稱':<40} {'任務類型':<12} {'needs_agent':<12} {'整體成功率':<12} {'平均耗時':<12} {'綜合評分':<10}"
    )
    print("-" * 80)

    for idx, (model_name, scores) in enumerate(sorted_models, 1):
        rank_icon = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        print(
            f"{rank_icon:<6} {model_name[:38]:<40} "
            f"{scores['task_type_accuracy']:>10.1f}% {scores['needs_agent_accuracy']:>10.1f}% "
            f"{scores['overall_success_rate']:>10.1f}% {scores['avg_time']:>10.2f}s "
            f"{scores['score']:>9.3f}"
        )

    print("\n" + "=" * 80)
    print(f"🏆 推薦模型（最適合意圖判斷）: {best_model}")
    print("=" * 80)

    if best_model:
        best_scores = analysis["model_scores"][best_model]
        print("\n推薦理由：")
        print(f"  - 任務類型識別正確率: {best_scores['task_type_accuracy']:.1f}%")
        print(f"  - needs_agent 正確率: {best_scores['needs_agent_accuracy']:.1f}%")
        print(f"  - 整體成功率: {best_scores['overall_success_rate']:.1f}%")
        print(f"  - 平均耗時: {best_scores['avg_time']:.2f}s")
        print(f"  - 綜合評分: {best_scores['score']:.3f}")


def main():
    """主函數"""
    import sys

    # 查找最新的 JSON 報告文件
    report_dir = Path(__file__).parent.parent.parent / "docs" / "系统设计文档" / "核心组件" / "Agent平台"

    json_files = sorted(
        report_dir.glob("router_llm_model_comparison_*.json"),
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not json_files:
        print("❌ 未找到測試報告文件")
        print(f"請先運行測試，報告應保存在: {report_dir}")
        sys.exit(1)

    latest_report = json_files[0]
    print(f"📄 分析報告文件: {latest_report.name}")
    print(
        f"📅 創建時間: {datetime.fromtimestamp(latest_report.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print()

    # 分析報告
    analysis = analyze_json_report(latest_report)

    # 打印結果
    print_analysis(analysis)

    # 保存分析結果
    analysis_file = report_dir / f"model_analysis_{latest_report.stem.split('_')[-1]}.json"
    with open(analysis_file, "w", encoding="utf-8") as f:
        json.dump(
            {
                "report_file": str(latest_report),
                "analysis": analysis,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(f"\n💾 分析結果已保存到: {analysis_file}")


if __name__ == "__main__":
    from datetime import datetime

    main()
