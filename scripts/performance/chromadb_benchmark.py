# 代碼功能說明: ChromaDB 性能測試腳本
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-25

"""
ChromaDB 性能測試腳本
用於測試批量寫入、檢索性能、並發性能等
"""

import os
import sys
import time
import statistics
import argparse
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

# 添加項目根目錄到路徑
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from database.chromadb import ChromaDBClient, ChromaCollection  # noqa: E402


def generate_embeddings(count: int, dimension: int = 384) -> List[List[float]]:
    """生成測試用的嵌入向量"""
    import random

    return [[random.random() for _ in range(dimension)] for _ in range(count)]


def benchmark_batch_write(
    collection: ChromaCollection,
    num_documents: int,
    batch_size: int = 100,
    embedding_dim: int = 384,
) -> Dict[str, Any]:
    """
    測試批量寫入性能

    Args:
        collection: ChromaDB 集合
        num_documents: 文檔數量
        batch_size: 批次大小
        embedding_dim: 嵌入向量維度

    Returns:
        性能統計字典
    """
    print(f"\n=== 批量寫入測試: {num_documents} 文檔, 批次大小: {batch_size} ===")

    embeddings = generate_embeddings(num_documents, embedding_dim)
    items = [
        {
            "id": f"doc_{i}",
            "embedding": embeddings[i],
            "metadata": {"index": i, "batch": i // batch_size},
            "document": f"Document {i}: This is a test document for performance testing.",
        }
        for i in range(num_documents)
    ]

    start_time = time.time()
    result = collection.batch_add(items, batch_size=batch_size)
    end_time = time.time()

    elapsed = end_time - start_time
    throughput = num_documents / elapsed if elapsed > 0 else 0

    stats = {
        "total_documents": num_documents,
        "batch_size": batch_size,
        "elapsed_time": elapsed,
        "throughput": throughput,  # 文檔/秒
        "success_count": result["success"],
        "failed_count": result["failed"],
        "avg_time_per_doc": elapsed / num_documents if num_documents > 0 else 0,
    }

    print(f"完成時間: {elapsed:.2f} 秒")
    print(f"吞吐量: {throughput:.2f} 文檔/秒")
    print(f"平均每文檔: {stats['avg_time_per_doc']*1000:.2f} 毫秒")
    print(f"成功: {result['success']}, 失敗: {result['failed']}")

    return stats


def benchmark_query(
    collection: ChromaCollection,
    num_queries: int = 100,
    n_results: int = 10,
    embedding_dim: int = 384,
) -> Dict[str, Any]:
    """
    測試檢索性能

    Args:
        collection: ChromaDB 集合
        num_queries: 查詢次數
        n_results: 每次查詢返回結果數
        embedding_dim: 嵌入向量維度

    Returns:
        性能統計字典
    """
    print(f"\n=== 檢索性能測試: {num_queries} 次查詢, 每次返回 {n_results} 結果 ===")

    query_embeddings = generate_embeddings(num_queries, embedding_dim)
    latencies = []
    errors = 0

    start_time = time.time()
    for i, query_emb in enumerate(query_embeddings):
        query_start = time.time()
        try:
            collection.query(query_embeddings=query_emb, n_results=n_results)
            query_end = time.time()
            latency = (query_end - query_start) * 1000  # 轉換為毫秒
            latencies.append(latency)

            if (i + 1) % 10 == 0:
                print(f"已完成 {i + 1}/{num_queries} 次查詢")
        except Exception as e:
            errors += 1
            print(f"查詢錯誤: {e}")

    end_time = time.time()
    total_elapsed = end_time - start_time

    if not latencies:
        return {"error": "所有查詢都失敗"}

    stats = {
        "total_queries": num_queries,
        "successful_queries": len(latencies),
        "failed_queries": errors,
        "total_elapsed_time": total_elapsed,
        "avg_latency_ms": statistics.mean(latencies),
        "p50_latency_ms": statistics.median(latencies),
        "p95_latency_ms": (
            statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20
            else latencies[-1]
        ),
        "p99_latency_ms": (
            statistics.quantiles(latencies, n=100)[98]
            if len(latencies) >= 100
            else latencies[-1]
        ),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "qps": num_queries / total_elapsed if total_elapsed > 0 else 0,
    }

    print("\n檢索性能統計:")
    print(f"總查詢數: {num_queries}")
    print(f"成功: {stats['successful_queries']}, 失敗: {errors}")
    print(f"平均延遲: {stats['avg_latency_ms']:.2f} 毫秒")
    print(f"P50 延遲: {stats['p50_latency_ms']:.2f} 毫秒")
    print(f"P95 延遲: {stats['p95_latency_ms']:.2f} 毫秒")
    print(f"P99 延遲: {stats['p99_latency_ms']:.2f} 毫秒")
    print(f"QPS: {stats['qps']:.2f}")

    return stats


def benchmark_concurrent_queries(
    collection: ChromaCollection,
    num_queries: int = 100,
    num_threads: int = 10,
    n_results: int = 10,
    embedding_dim: int = 384,
) -> Dict[str, Any]:
    """
    測試並發查詢性能

    Args:
        collection: ChromaDB 集合
        num_queries: 總查詢次數
        num_threads: 並發線程數
        n_results: 每次查詢返回結果數
        embedding_dim: 嵌入向量維度

    Returns:
        性能統計字典
    """
    print(f"\n=== 並發查詢測試: {num_queries} 次查詢, {num_threads} 線程 ===")

    query_embeddings = generate_embeddings(num_queries, embedding_dim)
    latencies = []
    errors = 0

    def query_worker(query_emb):
        try:
            start = time.time()
            collection.query(query_embeddings=query_emb, n_results=n_results)
            end = time.time()
            return (end - start) * 1000  # 毫秒
        except Exception as e:
            print(f"查詢錯誤: {e}")
            return None

    start_time = time.time()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(query_worker, emb) for emb in query_embeddings]
        for future in as_completed(futures):
            latency = future.result()
            if latency is not None:
                latencies.append(latency)
            else:
                errors += 1

    end_time = time.time()
    total_elapsed = end_time - start_time

    if not latencies:
        return {"error": "所有查詢都失敗"}

    stats = {
        "total_queries": num_queries,
        "num_threads": num_threads,
        "successful_queries": len(latencies),
        "failed_queries": errors,
        "total_elapsed_time": total_elapsed,
        "avg_latency_ms": statistics.mean(latencies),
        "p50_latency_ms": statistics.median(latencies),
        "p95_latency_ms": (
            statistics.quantiles(latencies, n=20)[18]
            if len(latencies) >= 20
            else latencies[-1]
        ),
        "p99_latency_ms": (
            statistics.quantiles(latencies, n=100)[98]
            if len(latencies) >= 100
            else latencies[-1]
        ),
        "min_latency_ms": min(latencies),
        "max_latency_ms": max(latencies),
        "qps": num_queries / total_elapsed if total_elapsed > 0 else 0,
    }

    print("\n並發查詢性能統計:")
    print(f"總查詢數: {num_queries}")
    print(f"並發線程數: {num_threads}")
    print(f"成功: {stats['successful_queries']}, 失敗: {errors}")
    print(f"平均延遲: {stats['avg_latency_ms']:.2f} 毫秒")
    print(f"P95 延遲: {stats['p95_latency_ms']:.2f} 毫秒")
    print(f"QPS: {stats['qps']:.2f}")

    return stats


def verify_performance_requirements(
    query_stats: Dict[str, Any],
    target_latency_ms: float = 200.0,
) -> Dict[str, Any]:
    """
    驗證性能要求

    Args:
        query_stats: 查詢性能統計
        target_latency_ms: 目標延遲（毫秒）

    Returns:
        驗證結果字典
    """
    print(f"\n=== 性能驗證 (目標: <{target_latency_ms}ms) ===")

    if "error" in query_stats:
        return {"passed": False, "reason": query_stats["error"]}

    p95_latency = query_stats.get("p95_latency_ms", float("inf"))
    avg_latency = query_stats.get("avg_latency_ms", float("inf"))

    passed = p95_latency < target_latency_ms

    result = {
        "passed": passed,
        "p95_latency_ms": p95_latency,
        "avg_latency_ms": avg_latency,
        "target_latency_ms": target_latency_ms,
        "meets_requirement": passed,
    }

    if passed:
        print("✅ 性能驗證通過!")
        print(f"   P95 延遲: {p95_latency:.2f}ms < {target_latency_ms}ms")
    else:
        print("❌ 性能驗證失敗!")
        print(f"   P95 延遲: {p95_latency:.2f}ms >= {target_latency_ms}ms")

    return result


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="ChromaDB 性能測試")
    parser.add_argument(
        "--mode",
        choices=["persistent", "http"],
        default="persistent",
        help="ChromaDB 連接模式",
    )
    parser.add_argument("--host", default="localhost", help="ChromaDB 主機（HTTP 模式）")
    parser.add_argument("--port", type=int, default=8001, help="ChromaDB 端口（HTTP 模式）")
    parser.add_argument(
        "--persist-dir",
        default="./benchmark_chroma_data",
        help="持久化目錄（持久化模式）",
    )
    parser.add_argument("--collection", default="benchmark_collection", help="測試集合名稱")
    parser.add_argument("--num-docs", type=int, default=1000, help="測試文檔數量")
    parser.add_argument("--batch-size", type=int, default=100, help="批量寫入批次大小")
    parser.add_argument("--num-queries", type=int, default=100, help="查詢次數")
    parser.add_argument("--n-results", type=int, default=10, help="每次查詢返回結果數")
    parser.add_argument("--embedding-dim", type=int, default=384, help="嵌入向量維度")
    parser.add_argument("--concurrent", action="store_true", help="執行並發測試")
    parser.add_argument("--num-threads", type=int, default=10, help="並發線程數")
    parser.add_argument("--target-latency", type=float, default=200.0, help="目標延遲（毫秒）")
    parser.add_argument("--output", help="輸出 JSON 報告文件路徑")

    args = parser.parse_args()

    print("=" * 60)
    print("ChromaDB 性能測試")
    print("=" * 60)
    print(f"模式: {args.mode}")
    print(f"集合: {args.collection}")
    print(f"文檔數量: {args.num_docs}")
    print(f"嵌入維度: {args.embedding_dim}")
    print("=" * 60)

    # 初始化客戶端
    try:
        if args.mode == "http":
            client = ChromaDBClient(
                mode="http",
                host=args.host,
                port=args.port,
            )
        else:
            client = ChromaDBClient(
                mode="persistent",
                persist_directory=args.persist_dir,
            )

        # 創建或獲取集合
        collection_obj = client.get_or_create_collection(args.collection)
        collection = ChromaCollection(
            collection_obj,
            expected_embedding_dim=args.embedding_dim,
            batch_size=args.batch_size,
        )

        # 清空集合（可選）
        try:
            collection.delete(where={})  # 刪除所有文檔
        except Exception:
            pass

        results = {}

        # 1. 批量寫入測試
        write_stats = benchmark_batch_write(
            collection,
            num_documents=args.num_docs,
            batch_size=args.batch_size,
            embedding_dim=args.embedding_dim,
        )
        results["batch_write"] = write_stats

        # 等待索引建立
        print("\n等待索引建立...")
        time.sleep(2)

        # 2. 檢索性能測試
        query_stats = benchmark_query(
            collection,
            num_queries=args.num_queries,
            n_results=args.n_results,
            embedding_dim=args.embedding_dim,
        )
        results["query"] = query_stats

        # 3. 並發測試（可選）
        if args.concurrent:
            concurrent_stats = benchmark_concurrent_queries(
                collection,
                num_queries=args.num_queries,
                num_threads=args.num_threads,
                n_results=args.n_results,
                embedding_dim=args.embedding_dim,
            )
            results["concurrent_query"] = concurrent_stats

        # 4. 性能驗證
        verification = verify_performance_requirements(
            query_stats,
            target_latency_ms=args.target_latency,
        )
        results["verification"] = verification

        # 輸出結果
        print("\n" + "=" * 60)
        print("測試完成")
        print("=" * 60)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            print(f"\n報告已保存到: {args.output}")

        # 清理
        client.delete_collection(args.collection)
        client.close()

        # 返回退出碼
        sys.exit(0 if verification.get("passed", False) else 1)

    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
