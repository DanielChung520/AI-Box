# 代碼功能說明: 大規模批量文件知識圖譜提取測試腳本（100個文件）
# 創建日期: 2026-01-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-02

"""大規模批量文件上傳和知識圖譜提取測試腳本

支持批量上傳100個文件，5個任務並發處理，詳細狀態記錄，失敗重試機制。
"""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import structlog

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = structlog.get_logger(__name__)

# API配置
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = os.getenv("API_PREFIX", "/api/v1")
TEST_USER_ID = os.getenv("TEST_USER_ID", "test-user")


class BatchTestClient:
    """批量測試客戶端類"""

    def __init__(self, base_url: str = API_BASE_URL, api_prefix: str = API_PREFIX):
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.client = httpx.AsyncClient(timeout=1800.0)  # 30分鐘超時
        self.results: List[Dict[str, Any]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def upload_file(
        self, file_path: str, task_id: Optional[str] = None, user_id: str = TEST_USER_ID
    ) -> Dict[str, Any]:
        """上傳文件"""
        url = f"{self.base_url}{self.api_prefix}/files/upload"

        with open(file_path, "rb") as f:
            files = {"files": (os.path.basename(file_path), f, "text/markdown")}
            data = {}
            if task_id:
                data["task_id"] = task_id

            response = await self.client.post(url, files=files, data=data)
            response.raise_for_status()
            return response.json()

    async def get_processing_status(self, file_id: str) -> Dict[str, Any]:
        """獲取處理狀態"""
        url = f"{self.base_url}{self.api_prefix}/files/{file_id}/processing-status"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def get_kg_stats(self, file_id: str) -> Dict[str, Any]:
        """獲取知識圖譜統計"""
        url = f"{self.base_url}{self.api_prefix}/files/{file_id}/kg/stats"
        response = await self.client.get(url)
        response.raise_for_status()
        return response.json()

    async def wait_for_processing(
        self, file_id: str, timeout: int = 3600, poll_interval: int = 5
    ) -> Dict[str, Any]:
        """等待處理完成"""
        start_time = time.time()
        last_status = None
        last_progress = -1
        consecutive_errors = 0
        max_consecutive_errors = 10

        while time.time() - start_time < timeout:
            try:
                status_response = await self.get_processing_status(file_id)

                if not status_response.get("success"):
                    error_msg = status_response.get("message", "未知錯誤")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        return {
                            "status": "error",
                            "progress": 0,
                            "error": f"連續{max_consecutive_errors}次API調用失敗",
                        }
                    await asyncio.sleep(poll_interval)
                    continue

                status_data = status_response.get("data", {})
                if not status_data:
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        return {"status": "error", "progress": 0, "error": "狀態數據為空"}
                    await asyncio.sleep(poll_interval)
                    continue

                consecutive_errors = 0

                status_value = status_data.get("status")
                progress = status_data.get("progress", 0)

                if status_value != last_status or progress != last_progress:
                    elapsed = time.time() - start_time
                    logger.info(
                        f"文件 {file_id[:8]}... 狀態: {status_value}, 進度: {progress}%, "
                        f"已等待: {elapsed:.1f}秒"
                    )
                    last_status = status_value
                    last_progress = progress

                if status_value == "completed":
                    elapsed = time.time() - start_time
                    logger.info(f"文件 {file_id[:8]}... 處理完成，總耗時: {elapsed:.2f}秒")
                    return {"status": "completed", "progress": 100, "processing_data": status_data}
                elif status_value == "failed":
                    error_msg = status_data.get("message", "處理失敗")
                    logger.error(f"文件 {file_id[:8]}... 處理失敗: {error_msg}")
                    return {
                        "status": "failed",
                        "progress": progress,
                        "error": error_msg,
                        "processing_data": status_data,
                    }

                await asyncio.sleep(poll_interval)
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    return {"status": "error", "progress": 0, "error": str(e)}
                await asyncio.sleep(poll_interval)

        elapsed = time.time() - start_time
        logger.error(f"文件 {file_id[:8]}... 等待超時（{elapsed:.1f}秒）")
        return {"status": "timeout", "progress": last_progress, "error": f"超時（{timeout}秒）"}

    def create_detailed_record(
        self,
        file_path: str,
        file_index: int,
        upload_time: Optional[float],
        processing_time: Optional[float],
        file_id: Optional[str],
        status: str,
        processing_data: Optional[Dict[str, Any]] = None,
        kg_stats: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        """創建詳細記錄（按照測試計劃要求）"""
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)

        record = {
            "file_info": {
                "file_name": file_name,
                "file_path": file_path,
                "file_size": file_size,
                "file_type": "text/markdown",
                "upload_time": datetime.now().isoformat() if upload_time else None,
                "processing_start_time": None,
                "processing_end_time": None,
                "file_id": file_id,
            },
            "vectorization": {
                "status": "❌",
                "vectorization_time": None,
                "chunk_count": None,
                "chunk_strategy": None,
                "collection_name": None,
                "embedding_dimension": None,
            },
            "kg_extraction": {
                "status": "❌",
                "extraction_time": None,
                "ontology": {
                    "base_ontology": False,
                    "domain_ontology": None,
                    "major_ontology": None,
                },
                "ner": {"entity_count": 0, "entity_types": []},
                "re": {"relation_count": 0, "relation_types": []},
                "rt": {"relation_type_count": 0},
                "arangodb": {
                    "entities_collection": "entities",
                    "relations_collection": "relations",
                    "entities_count": 0,
                    "relations_count": 0,
                },
            },
            "error_record": {
                "error_type": None,
                "error_message": None,
                "error_stack": None,
                "failed_stage": None,
            },
            "test_info": {
                "file_index": file_index,
                "test_timestamp": datetime.now().isoformat(),
                "retry_count": 0,
                "notes": [],
            },
        }

        if processing_time:
            record["file_info"]["processing_start_time"] = (
                datetime.fromtimestamp(time.time() - processing_time).isoformat()
                if upload_time
                else None
            )
            record["file_info"]["processing_end_time"] = datetime.now().isoformat()

        if processing_data:
            vectorization_data = processing_data.get("vectorization", {})
            if vectorization_data.get("status") == "completed":
                record["vectorization"]["status"] = "✅"
                record["vectorization"]["chunk_count"] = vectorization_data.get("chunk_count")
                record["vectorization"]["collection_name"] = vectorization_data.get(
                    "collection_name"
                )

            storage_data = processing_data.get("storage", {})
            if storage_data.get("status") == "completed":
                record["vectorization"]["chunk_count"] = storage_data.get("vector_count")

            kg_data = processing_data.get("kg_extraction", {})
            if kg_data.get("status") == "completed":
                record["kg_extraction"]["status"] = "✅"
                record["kg_extraction"]["extraction_time"] = kg_data.get("extraction_time")
                record["kg_extraction"]["ner"]["entity_count"] = kg_data.get("entities_count", 0)
                record["kg_extraction"]["re"]["relation_count"] = kg_data.get("relations_count", 0)

        if kg_stats:
            record["kg_extraction"]["arangodb"]["entities_count"] = kg_stats.get(
                "entities_count", 0
            )
            record["kg_extraction"]["arangodb"]["relations_count"] = kg_stats.get(
                "relations_count", 0
            )
            record["kg_extraction"]["ner"]["entity_count"] = kg_stats.get("entities_count", 0)
            record["kg_extraction"]["re"]["relation_count"] = kg_stats.get("relations_count", 0)

        if error or status in ["failed", "error", "timeout"]:
            record["error_record"]["error_type"] = status
            record["error_record"]["error_message"] = error
            if processing_data:
                if processing_data.get("vectorization", {}).get("status") == "failed":
                    record["error_record"]["failed_stage"] = "向量化"
                elif processing_data.get("kg_extraction", {}).get("status") == "failed":
                    record["error_record"]["failed_stage"] = "知識圖譜提取"
                else:
                    record["error_record"]["failed_stage"] = "上傳"
            else:
                record["error_record"]["failed_stage"] = "上傳"

        return record

    async def process_single_file(
        self, file_path: str, file_index: int, total_files: int, retry_count: int = 0
    ) -> Dict[str, Any]:
        """處理單個文件"""
        file_name = os.path.basename(file_path)

        if retry_count > 0:
            logger.info(f"[重試 {retry_count}] [{file_index}/{total_files}] 開始處理: {file_name}")
        else:
            logger.info(f"[{file_index}/{total_files}] 開始處理: {file_name}")

        result = {
            "file_path": file_path,
            "file_name": file_name,
            "file_index": file_index,
            "upload_time": None,
            "processing_time": None,
            "status": "pending",
            "file_id": None,
            "error": None,
            "kg_stats": None,
            "processing_data": None,
            "retry_count": retry_count,
        }

        try:
            upload_start = time.time()
            upload_response = await self.upload_file(file_path)
            upload_time = time.time() - upload_start

            if upload_response.get("success"):
                data = upload_response.get("data", {})
                uploaded_files = data.get("uploaded", [])
                if uploaded_files:
                    file_id = uploaded_files[0].get("file_id")
                    if file_id:
                        result["file_id"] = file_id
                        result["upload_time"] = upload_time
                        logger.info(
                            f"[{file_index}/{total_files}] 上傳成功: {file_name} (ID: {file_id[:8]}...)"
                        )

                        processing_start = time.time()
                        processing_result = await self.wait_for_processing(file_id, timeout=3600)
                        processing_time = time.time() - processing_start

                        result["processing_time"] = processing_time
                        result["status"] = processing_result.get("status", "unknown")
                        result["processing_data"] = processing_result.get("processing_data")

                        if processing_result.get("status") == "completed":
                            try:
                                kg_stats_response = await self.get_kg_stats(file_id)
                                if kg_stats_response.get("success"):
                                    result["kg_stats"] = kg_stats_response.get("data", {})
                            except Exception as e:
                                logger.warning(f"獲取KG統計失敗: {e}")

                            logger.info(
                                f"[{file_index}/{total_files}] 處理完成: {file_name} "
                                f"(時間: {processing_time:.2f}秒)"
                            )
                        else:
                            result["error"] = processing_result.get("error", "處理失敗")
                            logger.error(
                                f"[{file_index}/{total_files}] 處理失敗: {file_name} "
                                f"(狀態: {processing_result.get('status')})"
                            )
                    else:
                        result["status"] = "failed"
                        result["error"] = "無法從上傳響應中獲取file_id"
                else:
                    result["status"] = "failed"
                    result["error"] = "上傳響應中沒有uploaded數組"
            else:
                result["status"] = "failed"
                result["error"] = upload_response.get("message", "上傳失敗")

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)
            logger.error(f"[{file_index}/{total_files}] 處理錯誤: {file_name} - {e}")

        detailed_record = self.create_detailed_record(
            file_path=file_path,
            file_index=file_index,
            upload_time=result.get("upload_time"),
            processing_time=result.get("processing_time"),
            file_id=result.get("file_id"),
            status=result.get("status"),
            processing_data=result.get("processing_data"),
            kg_stats=result.get("kg_stats"),
            error=result.get("error"),
        )
        detailed_record["test_info"]["retry_count"] = retry_count
        result["detailed_record"] = detailed_record

        return result

    async def process_files_batch(
        self, file_paths: List[str], max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """批量處理文件（支持並發）"""
        total_files = len(file_paths)
        logger.info(f"開始批量處理 {total_files} 個文件，並發數: {max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)
        results: List[Dict[str, Any]] = []

        async def process_with_semaphore(file_path: str, index: int):
            async with semaphore:
                return await self.process_single_file(file_path, index, total_files, retry_count=0)

        tasks = [
            process_with_semaphore(file_path, index + 1)
            for index, file_path in enumerate(file_paths)
        ]

        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(
                    {
                        "file_path": file_paths[i],
                        "file_name": os.path.basename(file_paths[i]),
                        "status": "error",
                        "error": str(result),
                        "detailed_record": {
                            "error_record": {
                                "error_message": str(result),
                                "error_type": "exception",
                            },
                        },
                    }
                )
            else:
                processed_results.append(result)

        total_time = time.time() - start_time
        logger.info(f"批量處理完成，總時間: {total_time:.2f}秒")

        return processed_results

    async def retry_failed_files(
        self, failed_results: List[Dict[str, Any]], max_concurrent: int = 5
    ) -> List[Dict[str, Any]]:
        """重試失敗的文件"""
        if not failed_results:
            logger.info("沒有失敗的文件需要重試")
            return []

        total_files = len(failed_results)
        logger.info(f"開始重試 {total_files} 個失敗的文件，並發數: {max_concurrent}")

        semaphore = asyncio.Semaphore(max_concurrent)
        retry_results = []

        async def retry_with_semaphore(result: Dict[str, Any], index: int):
            async with semaphore:
                retry_count = result.get("retry_count", 0) + 1
                detailed_record = result.get("detailed_record", {})
                test_info = detailed_record.get("test_info", {})
                test_info.setdefault("notes", []).append(
                    f"第一次失敗後重試（重試次數: {retry_count}）"
                )

                return await self.process_single_file(
                    result["file_path"],
                    result["file_index"],
                    total_files,
                    retry_count=retry_count,
                )

        tasks = [
            retry_with_semaphore(result, index + 1) for index, result in enumerate(failed_results)
        ]

        start_time = time.time()
        retry_results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_retry_results = []
        for i, result in enumerate(retry_results):
            if isinstance(result, Exception):
                failed_result = failed_results[i]
                failed_result["status"] = "error"
                failed_result["error"] = f"重試時發生異常: {str(result)}"
                detailed_record = failed_result.get("detailed_record", {})
                test_info = detailed_record.get("test_info", {})
                test_info.setdefault("notes", []).append(f"重試時發生異常: {str(result)}")
                processed_retry_results.append(failed_result)
            else:
                processed_retry_results.append(result)

        total_time = time.time() - start_time
        logger.info(f"重試完成，總時間: {total_time:.2f}秒")

        return processed_retry_results


def save_results(results: List[Dict[str, Any]], output_file: str, progress_file: str):
    """保存測試結果和進度"""
    total_files = len(results)
    success_count = sum(1 for r in results if r.get("status") == "completed")
    failed_count = sum(1 for r in results if r.get("status") in ["failed", "error", "timeout"])
    timeout_count = sum(1 for r in results if r.get("status") == "timeout")

    completed_times = [r.get("processing_time", 0) for r in results if r.get("processing_time")]
    avg_processing_time = sum(completed_times) / len(completed_times) if completed_times else 0

    total_entities = 0
    total_relations = 0
    for result in results:
        kg_stats = result.get("kg_stats", {})
        if kg_stats:
            total_entities += kg_stats.get("entities_count", 0)
            total_relations += kg_stats.get("relations_count", 0)

    summary = {
        "total_files": total_files,
        "success_count": success_count,
        "failed_count": failed_count,
        "timeout_count": timeout_count,
        "success_rate": (success_count / total_files * 100) if total_files > 0 else 0,
        "total_processing_time": sum(completed_times),
        "avg_processing_time": avg_processing_time,
        "total_entities": total_entities,
        "total_relations": total_relations,
        "test_timestamp": datetime.now().isoformat(),
        "test_duration_seconds": sum(completed_times),
    }

    output_data = {
        "summary": summary,
        "results": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    progress_data = {
        "last_update": datetime.now().isoformat(),
        "summary": summary,
        "files": [
            {
                "file_name": r.get("file_name"),
                "file_index": r.get("file_index"),
                "status": r.get("status"),
                "progress": 100 if r.get("status") == "completed" else 0,
            }
            for r in results
        ],
    }

    with open(progress_file, "w", encoding="utf-8") as f:
        json.dump(progress_data, f, ensure_ascii=False, indent=2)

    logger.info(f"測試結果已保存到: {output_file}")
    logger.info(f"進度文件已保存到: {progress_file}")
    return summary


def print_summary(summary: Dict[str, Any]):
    """打印測試摘要"""
    print("\n" + "=" * 80)
    print("大規模批量測試結果摘要")
    print("=" * 80)
    print(f"總文件數: {summary['total_files']}")
    print(f"成功處理: {summary['success_count']} ({summary['success_rate']:.1f}%)")
    print(f"失敗處理: {summary['failed_count']}")
    print(f"超時: {summary['timeout_count']}")
    print(
        f"總處理時間: {summary['total_processing_time']:.2f}秒 ({summary['total_processing_time']/60:.1f}分鐘)"
    )
    print(f"平均處理時間: {summary['avg_processing_time']:.2f}秒/文件")
    print(f"總實體數: {summary['total_entities']}")
    print(f"總關係數: {summary['total_relations']}")
    print("=" * 80)


async def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="大規模批量文件知識圖譜提取測試（100個文件）")
    parser.add_argument("--file-list", type=str, help="包含文件路徑列表的文件（每行一個路徑）")
    parser.add_argument("--max-files", type=int, default=100, help="最大處理文件數（默認: 100）")
    parser.add_argument("--concurrent", type=int, default=5, help="並發任務數（默認: 5）")
    parser.add_argument(
        "--output", type=str, default="batch_test_100_results.json", help="輸出結果文件"
    )
    parser.add_argument(
        "--progress", type=str, default="batch_test_100_progress.json", help="進度文件"
    )
    parser.add_argument("--retry-failed", action="store_true", help="是否重試失敗的文件")
    parser.add_argument("--input-dir", type=str, help="輸入目錄（將處理目錄下所有 .md 文件）")

    args = parser.parse_args()

    file_paths = []

    if args.file_list:
        with open(args.file_list, "r", encoding="utf-8") as f:
            file_paths = [
                line.strip() for line in f if line.strip() and not line.strip().startswith("#")
            ]
    elif args.input_dir:
        input_dir = Path(args.input_dir)
        file_paths = [str(f) for f in input_dir.rglob("*.md")]
        file_paths = sorted(file_paths)[: args.max_files]
    else:
        docs_dir = project_root / "docs" / "系统设计文档"
        file_paths = [str(f) for f in docs_dir.rglob("*.md")]
        file_paths = sorted(file_paths)[: args.max_files]

    if not file_paths:
        logger.error("沒有找到要處理的文件")
        return

    logger.info(f"準備處理 {len(file_paths)} 個文件，並發數: {args.concurrent}")

    async with BatchTestClient() as client:
        results = await client.process_files_batch(file_paths, max_concurrent=args.concurrent)

        summary = save_results(results, args.output, args.progress)

        if args.retry_failed:
            failed_results = [
                r for r in results if r.get("status") in ["failed", "error", "timeout"]
            ]
            if failed_results:
                logger.info(f"準備重試 {len(failed_results)} 個失敗的文件")
                retry_results = await client.retry_failed_files(
                    failed_results, max_concurrent=args.concurrent
                )

                final_results = []
                retry_index = 0
                for result in results:
                    if result.get("status") in ["failed", "error", "timeout"]:
                        if retry_index < len(retry_results):
                            final_results.append(retry_results[retry_index])
                            retry_index += 1
                        else:
                            final_results.append(result)
                    else:
                        final_results.append(result)

                final_summary = save_results(
                    final_results,
                    args.output.replace(".json", "_with_retry.json"),
                    args.progress.replace(".json", "_with_retry.json"),
                )
                print_summary(final_summary)
            else:
                print_summary(summary)
        else:
            print_summary(summary)


if __name__ == "__main__":
    asyncio.run(main())
