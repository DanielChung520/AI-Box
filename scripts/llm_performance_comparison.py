# 代碼功能說明: LLM 模型效能比較測試腳本（檔案上傳與知識圖譜提取）
# 創建日期: 2026-01-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-20

"""LLM 模型效能比較測試腳本

測試目標：
1. 比較 5 個 Ollama 模型在知識圖譜提取任務上的效能
2. 測量指標：提取時間、Entity 數量、Edge/Relation 數量
3. 記錄結果並選擇最佳模型

測試模型：
- gpt-oss:120b-cloud
- glm-4.7:cloud
- glm-4.6:cloud
- qwen3-next:latest
- mistral-nemo:12b

使用方法：
    python scripts/llm_performance_comparison.py

    # 只測試特定模型
    python scripts/llm_performance_comparison.py --models gpt-oss:120b-cloud mistral-nemo:12b

    # 指定測試文件
    python scripts/llm_performance_comparison.py --test-file path/to/test.md
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加項目根目錄到 Python 路徑
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# 測試模型列表
TEST_MODELS = [
    "gpt-oss:120b-cloud",
    "glm-4.7:cloud",
    "glm-4.6:cloud",
    "qwen3-next:latest",
    "mistral-nemo:12b",
]

# 預設測試文本（模擬系統文檔內容）
DEFAULT_TEST_TEXT = """# 系統架構說明

AI-Box 是一個 AI 輔助軟體開發平台。本系統使用 FastAPI 作為後端框架，數據庫採用 ArangoDB 圖資料庫和 ChromaDB 向量資料庫。存儲服務使用 SeaweedFS，任務隊列使用 Redis + RQ。LLM 整合採用 MoE（Mixture of Experts）架構。

系統主要包含以下組件：API 服務、Agent 實作、數據庫客戶端、知識圖譜模組、LLM 客戶端、MCP 工具、業務邏輯服務和存儲服務。API 服務運行在 8000 端口，ArangoDB 在 8529 端口，Redis 在 6379 端口，SeaweedFS S3 在 8333 端口，Ollama 在 11434 端口。

系統配置通過 config/config.json 文件管理，環境變數包括 AI_BOX_CONFIG_PATH、OLLAMA_HOST、ARANGODB_HOST 等。主要的 LLM 提供商包括 ChatGPT、Gemini、Qwen、Grok 和本地 Ollama 模型。

系統支持文件上傳功能，支援的格式包括 PDF、DOCX、TXT、MD、CSV、JSON、HTML 和 XLSX。上傳的檔案會經過處理，分塊後存入向量資料庫，同時提取知識圖譜三元組存入 ArangoDB。

知識圖譜提取使用 NER（命名實體識別）和 RE（關係抽取）技術。NER 模型預設使用 llama3.1:8b，回退到 qwen3-vl:8b。關係抽取模型使用 bert-base-chinese。

系統提供 RESTful API，主要端點包括 /api/v1/files/upload 用於上傳文件，/api/v1/files/{file_id}/processing-status 用於查詢處理狀態，/api/v1/files/{file_id}/kg/stats 用於查詢知識圖譜統計。

文件處理流程分為三個階段：首先是文件上傳和存儲，然後是分塊和向量化，最後是知識圖譜提取。每個階段都有對應的服務和狀態追蹤。

系統安全性方面，支援 JWT 認證、API Key 認證和 RBAC 權限控制。在開發環境中可以禁用安全功能。

監控功能包括 Prometheus 指標收集和 Grafana 儀表板。任務佇列監控使用 RQ Dashboard。

系統部署支援 Kubernetes，命名空間為 ai-box。監控命名空間為 ai-box-monitoring。

系統文檔保存在 docs/系統設計文檔/ 目錄下，包括架構說明、API 文檔和部署指南。

用戶可以通過 Web 介面或 API 與系統互動。系統支持多用戶模式，每個用戶有獨立的工作空間和任務歷史。

系統性能優化包括：使用連接池管理數據庫連接、使用異步處理提高並發能力、使用緩存減少重複計算。

系統維護功能包括：數據備份、日誌清理、性能監控和健康檢查。健康檢查端點為 /health。

系統擴展性設計支援水平擴展，可以通過增加實例數量來提高處理能力。各服務之間通過消息隊列進行解耦。

錯誤處理採用統一的異常捕獲和日誌記錄機制，支援重試機制和降級策略。

日誌格式使用標準 Python logging，不使用 structlog 格式，以便與標準工具兼容。

代碼規範要求：文件頭必須包含功能說明、創建日期、創建人和最後修改日期。所有函數必須有類型注解。

開發環境配置需要設置以下環境變數：AI_BOX_CONFIG_PATH、OLLAMA_HOST、ARANGODB_HOST、REDIS_HOST 和 SEAWEEDFS_HOST。

測試框架使用 pytest，支持單元測試、整合測試和效能測試。測試覆蓋率目標為 80% 以上。

持續整合使用 GitHub Actions，自動化執行測試、程式碼檢查和部署流程。

版本管理使用 Git，遵循 Git Flow 工作流程。主分支受到保護，所有修改必須通過 Pull Request 審核。

代碼審查要求：每個 Pull Request 至少需要一人審核，審查重點包括程式碼質量、測試覆蓋和文檔更新。

文檔更新隨程式碼一起提交，確保文檔與實際行為一致。重大變更需要更新多個相關文檔。

系統回滾機制支援快速回滾到上一個穩定版本，回滾過程自動完成，無需人工干預。

用戶反饋渠道包括：GitHub Issues、系統內建反饋表單和定期用戶調查。用戶反饋用於優先排序開發任務。

系統未來規劃包括：支援更多 LLM 模型、改進知識圖譜提取精度、加強監控和報警功能，以及優化用戶介面體驗。
"""

# 全局結果存儲
_test_results: List[Dict[str, Any]] = []


def get_ollama_client(model_name: str):
    """創建 Ollama 客戶端實例"""
    from llm.clients.ollama import OllamaClient
    from llm.router import LLMNodeConfig, LLMNodeRouter

    localhost_node = LLMNodeConfig(
        name="localhost",
        host="localhost",
        port=11434,
        weight=1,
    )
    router = LLMNodeRouter(
        nodes=[localhost_node],
        strategy="round_robin",
        cooldown_seconds=30,
    )
    return OllamaClient(router=router, default_model=model_name)


async def test_model_extraction(
    model_name: str,
    test_text: str,
    timeout: float = 300.0,
) -> Dict[str, Any]:
    """
    測試單個模型的知识图谱提取效能

    Args:
        model_name: 模型名稱
        test_text: 測試文本
        timeout: 超時時間（秒）

    Returns:
        測試結果字典
    """
    import structlog

    logger = structlog.get_logger(__name__)

    start_time = time.time()

    try:
        client = get_ollama_client(model_name)

        if not client.is_available():
            return {
                "model": model_name,
                "success": False,
                "error": "Client not available",
                "elapsed_time": 0,
                "entities_count": 0,
                "relations_count": 0,
            }

        # 構建知識圖譜提取提示詞
        prompt = f"""你是一個知識圖譜提取專家。請從以下文本中提取實體和關係，以 JSON 格式輸出。

要求：
1. 提取所有命名實體（人名、組織、系統、服務、概念等）
2. 提取實體之間的關係
3. 只輸出 JSON，不要其他說明

文本：
{test_text}

輸出格式：
{{
    "entities": [
        {{"name": "實體名稱", "type": "實體類型"}}
    ],
    "relations": [
        {{"from": "來源實體", "to": "目標實體", "relation": "關係類型"}}
    ]
}}
"""

        messages = [
            {"role": "system", "content": "你是一個知識圖譜提取專家。"},
            {"role": "user", "content": prompt},
        ]

        # 發送請求並設置超時
        try:
            result = await asyncio.wait_for(
                client.chat(messages, model=model_name, temperature=0.1),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            return {
                "model": model_name,
                "success": False,
                "error": f"Timeout after {timeout}s",
                "elapsed_time": timeout,
                "entities_count": 0,
                "relations_count": 0,
            }

        elapsed_time = time.time() - start_time

        # 解析結果
        content = result.get("content", "") or result.get("message", "")

        # 提取 JSON
        import re

        json_match = re.search(r"\{[\s\S]*\}", content)
        if json_match:
            try:
                kg_data = json.loads(json_match.group())
                entities = kg_data.get("entities", [])
                relations = kg_data.get("relations", [])
                entities_count = len(entities)
                relations_count = len(relations)
            except json.JSONDecodeError:
                entities_count = 0
                relations_count = 0
        else:
            entities_count = 0
            relations_count = 0

        return {
            "model": model_name,
            "success": True,
            "error": None,
            "elapsed_time": elapsed_time,
            "entities_count": entities_count,
            "relations_count": relations_count,
            "raw_content": content[:500] if len(content) > 500 else content,
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Model {model_name} extraction error: {e}")
        return {
            "model": model_name,
            "success": False,
            "error": str(e),
            "elapsed_time": elapsed_time,
            "entities_count": 0,
            "relations_count": 0,
        }


def generate_comparison_report(results: List[Dict[str, Any]], output_file: Optional[str] = None):
    """生成模型比較報告"""
    print("\n" + "=" * 80)
    print("LLM 知識圖譜提取效能比較報告")
    print("=" * 80)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"測試文本長度: {len(DEFAULT_TEST_TEXT)} 字元")

    # 按模型分組統計
    model_stats: Dict[str, Dict[str, Any]] = {}
    for model in TEST_MODELS:
        model_results = [r for r in results if r["model"] == model]
        if not model_results:
            continue

        success_count = sum(1 for r in model_results if r["success"])
        total_time = sum(r["elapsed_time"] for r in model_results)
        avg_time = total_time / len(model_results)
        total_entities = sum(r["entities_count"] for r in model_results)
        total_relations = sum(r["relations_count"] for r in model_results)
        avg_entities = total_entities / len(model_results)
        avg_relations = total_relations / len(model_results)

        model_stats[model] = {
            "success_rate": success_count / len(model_results) * 100,
            "avg_time": avg_time,
            "total_time": total_time,
            "avg_entities": avg_entities,
            "total_entities": total_entities,
            "avg_relations": avg_relations,
            "total_relations": total_relations,
        }

    # 打印比較表格
    print("\n| 模型 | 成功率 | 平均耗時 | 總耗時 | 平均 Entity | 平均 Relation |")
    print("|------|--------|----------|--------|-------------|---------------|")
    for model in TEST_MODELS:
        if model not in model_stats:
            print(f"| {model[:20]:20} | N/A | N/A | N/A | N/A | N/A |")
            continue
        stats = model_stats[model]
        print(
            f"| {model[:20]:20} | {stats['success_rate']:6.1f}% | "
            f"{stats['avg_time']:8.2f}s | {stats['total_time']:7.2f}s | "
            f"{stats['avg_entities']:11.1f} | {stats['avg_relations']:13.1f} |"
        )

    # 計算綜合得分
    print("\n" + "=" * 80)
    print("綜合評估")
    print("=" * 80)

    # 計算得分（時間越短越好，Entity/Relation 越多越好）
    scores: Dict[str, float] = {}
    if model_stats:
        # 找到最佳值
        min_time = min(s["avg_time"] for s in model_stats.values())
        max_entities = max(s["avg_entities"] for s in model_stats.values())
        max_relations = max(s["avg_relations"] for s in model_stats.values())

        for model, stats in model_stats.items():
            # 時間得分（0-40分）：時間越短分數越高
            time_score = (min_time / stats["avg_time"]) * 40 if stats["avg_time"] > 0 else 0

            # Entity 得分（0-30分）
            entity_score = (stats["avg_entities"] / max_entities) * 30 if max_entities > 0 else 0

            # Relation 得分（0-30分）
            relation_score = (
                (stats["avg_relations"] / max_relations) * 30 if max_relations > 0 else 0
            )

            total_score = time_score + entity_score + relation_score
            scores[model] = total_score

    # 打印得分排名
    print("\n模型得分排名（越高越好）：")
    print("| 排名 | 模型 | 總得分 | 時間得分 | Entity 得分 | Relation 得分 |")
    print("|------|------|--------|----------|-------------|---------------|")

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    for rank, (model, score) in enumerate(sorted_scores, 1):
        stats = model_stats.get(model, {})
        min_time = min(s["avg_time"] for s in model_stats.values()) if model_stats else 1
        max_entities = max(s["avg_entities"] for s in model_stats.values()) if model_stats else 1
        max_relations = max(s["avg_relations"] for s in model_stats.values()) if model_stats else 1

        time_score = (min_time / stats["avg_time"]) * 40 if stats["avg_time"] > 0 else 0
        entity_score = (stats["avg_entities"] / max_entities) * 30 if max_entities > 0 else 0
        relation_score = (stats["avg_relations"] / max_relations) * 30 if max_relations > 0 else 0

        print(
            f"| {rank:4} | {model[:16]:16} | {score:6.1f} | "
            f"{time_score:8.1f} | {entity_score:11.1f} | {relation_score:13.1f} |"
        )

    # 推薦最佳模型
    if sorted_scores:
        best_model = sorted_scores[0][0]
        print(f"\n推薦模型：{best_model}")

    # 保存 JSON 報告
    if output_file:
        report_data = {
            "test_time": datetime.now().isoformat(),
            "test_text_length": len(DEFAULT_TEST_TEXT),
            "models": TEST_MODELS,
            "results": results,
            "statistics": model_stats,
            "scores": scores,
            "recommended_model": sorted_scores[0][0] if sorted_scores else None,
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"\n報告已保存到: {output_file}")


async def run_performance_test(
    models: Optional[List[str]] = None,
    test_text: Optional[str] = None,
    iterations: int = 1,
):
    """運行效能測試"""
    import structlog

    logger = structlog.get_logger(__name__)

    if models is None:
        models = TEST_MODELS

    if test_text is None:
        test_text = DEFAULT_TEST_TEXT

    print("=" * 80)
    print("LLM 知識圖譜提取效能測試")
    print("=" * 80)
    print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n測試模型數量: {len(models)}")
    print(f"測試迭代次數: {iterations}")
    print(f"測試文本長度: {len(test_text)} 字元")
    print("\n測試模型列表:")
    for i, model in enumerate(models, 1):
        print(f"  {i}. {model}")

    print("\n" + "=" * 80)
    print("開始測試...")
    print("=" * 80)

    all_results: List[Dict[str, Any]] = []

    for model_idx, model_name in enumerate(models, 1):
        print(f"\n[{model_idx}/{len(models)}] 測試模型: {model_name}")
        print("-" * 80)

        model_results = []
        for iteration in range(1, iterations + 1):
            print(f"  迭代 [{iteration}/{iterations}]...", end=" ")
            result = await test_model_extraction(model_name, test_text)
            model_results.append(result)
            all_results.append(result)

            if result["success"]:
                print(
                    f"✅ 耗時={result['elapsed_time']:.2f}s, "
                    f"Entities={result['entities_count']}, "
                    f"Relations={result['relations_count']}"
                )
            else:
                print(f"❌ 錯誤: {result['error']}")

        # 計算模型統計
        success_count = sum(1 for r in model_results if r["success"])
        total_time = sum(r["elapsed_time"] for r in model_results)
        avg_time = total_time / len(model_results)
        avg_entities = sum(r["entities_count"] for r in model_results) / len(model_results)
        avg_relations = sum(r["relations_count"] for r in model_results) / len(model_results)

        print(f"\n  模型統計 ({model_name}):")
        print(
            f"    成功率: {success_count}/{len(model_results)} ({success_count / len(model_results) * 100:.1f}%)"
        )
        print(f"    平均耗時: {avg_time:.2f}s")
        print(f"    平均 Entity 數量: {avg_entities:.1f}")
        print(f"    平均 Relation 數量: {avg_relations:.1f}")

    # 生成比較報告
    report_file = (
        Path(__file__).parent.parent
        / "docs"
        / "系統設計文檔"
        / "核心組件"
        / "文件上傳向量圖譜"
        / f"llm_performance_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    generate_comparison_report(all_results, str(report_file))

    print("\n" + "=" * 80)
    print("測試完成")
    print("=" * 80)

    return all_results


def main():
    """主函數"""
    import argparse

    parser = argparse.ArgumentParser(description="LLM 知識圖譜提取效能測試")
    parser.add_argument(
        "--models",
        nargs="+",
        default=None,
        help="指定測試的模型列表",
    )
    parser.add_argument(
        "--test-file",
        type=str,
        default=None,
        help="指定測試文件路徑",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="測試迭代次數（預設: 1）",
    )

    args = parser.parse_args()

    # 讀取測試文件
    test_text = None
    if args.test_file:
        test_file_path = Path(args.test_file)
        if test_file_path.exists():
            test_text = test_file_path.read_text(encoding="utf-8")
            print(f"已載入測試文件: {test_file_path}")
        else:
            print(f"錯誤: 測試文件不存在: {test_file_path}")

    # 運行測試
    results = asyncio.run(
        run_performance_test(models=args.models, test_text=test_text, iterations=args.iterations)
    )

    return results


if __name__ == "__main__":
    main()
