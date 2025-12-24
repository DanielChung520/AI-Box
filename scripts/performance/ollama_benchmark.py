# 代碼功能說明: 對 /api/v1/llm/generate 執行簡易壓測並輸出延遲統計
# 創建日期: 2025-11-26 00:45 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 00:45 (UTC+8)
#!/usr/bin/env python3

"""Ollama LLM API 壓測工具。"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx

DEFAULT_ENDPOINT = "http://localhost:8000/api/v1/llm/generate"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark /api/v1/llm/generate latency.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="API 端點")
    parser.add_argument("--model", default=None, help="覆寫模型名稱")
    parser.add_argument("--prompt", default="ping", help="測試 prompt 內容")
    parser.add_argument("--requests", type=int, default=20, help="總請求數")
    parser.add_argument("--concurrency", type=int, default=5, help="並發度")
    parser.add_argument("--timeout", type=float, default=15.0, help="單次請求逾時秒數")
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/performance/ollama-load-test-result.json"),
        help="結果輸出檔案",
    )
    return parser.parse_args()


async def benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    semaphore = asyncio.Semaphore(args.concurrency)
    latencies: List[float] = []
    failures: List[str] = []

    async def run_single(index: int) -> None:
        payload = {"prompt": args.prompt, "stream": False}
        if args.model:
            payload["model"] = args.model
        async with semaphore:
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=args.timeout) as client:
                    response = await client.post(args.endpoint, json=payload)
                    response.raise_for_status()
                    latencies.append(time.perf_counter() - start)
            except Exception as exc:  # noqa: BLE001
                failures.append(f"#{index}: {exc}")

    await asyncio.gather(*(run_single(i) for i in range(args.requests)))

    summary = {
        "endpoint": args.endpoint,
        "model": args.model,
        "prompt": args.prompt,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "success": len(latencies),
        "failed": len(failures),
    }
    if latencies:
        summary.update(
            {
                "latency_avg_ms": statistics.mean(latencies) * 1000,
                "latency_p95_ms": statistics.quantiles(latencies, n=20)[-1] * 1000,
                "latency_min_ms": min(latencies) * 1000,
                "latency_max_ms": max(latencies) * 1000,
            }
        )
    summary["failures"] = failures
    return summary


def save_report(report_path: Path, data: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    print(f"Report saved to {report_path}")


def main() -> None:
    args = parse_args()
    summary = asyncio.run(benchmark(args))
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    save_report(args.report, summary)


if __name__ == "__main__":
    main()
