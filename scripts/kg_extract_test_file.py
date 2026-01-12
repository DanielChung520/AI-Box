# 代碼功能說明: 單一文件知識圖譜提取測試腳本
# 創建日期: 2026-01-01
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""單一文件上傳和知識圖譜提取測試腳本

支持測試文件上傳、向量化和知識圖譜提取的完整流程。
支持Ollama和Gemini兩種模型的對比測試。
"""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

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


class TestClient:
    """測試客戶端類"""

    def __init__(self, base_url: str = API_BASE_URL, api_prefix: str = API_PREFIX):
        self.base_url = base_url
        self.api_prefix = api_prefix
        self.client = httpx.AsyncClient(timeout=300.0)  # 5分鐘超時
        self.token: Optional[str] = None

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

    async def get_kg_triples(
        self, file_id: str, limit: int = 100, offset: int = 0
    ) -> Dict[str, Any]:
        """獲取知識圖譜三元組"""
        url = f"{self.base_url}{self.api_prefix}/files/{file_id}/kg/triples"
        params = {"limit": limit, "offset": offset}
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def wait_for_processing(
        self, file_id: str, timeout: int = 600, poll_interval: int = 2
    ) -> Dict[str, Any]:
        """等待處理完成"""
        start_time = time.time()
        last_status = None

        while time.time() - start_time < timeout:
            try:
                status_response = await self.get_processing_status(file_id)
                last_status = status_response

                status_data = status_response.get("data", {})
                status_value = status_data.get("status")
                progress = status_data.get("progress", 0)

                logger.info(
                    "Processing status",
                    file_id=file_id,
                    status=status_value,
                    progress=progress,
                )

                if status_value == "completed":
                    return status_response
                elif status_value == "failed":
                    error_msg = status_data.get("message", "Unknown error")
                    raise RuntimeError(f"Processing failed: {error_msg}")

                await asyncio.sleep(poll_interval)
            except Exception as e:
                logger.warning("Failed to get status", error=str(e))
                await asyncio.sleep(poll_interval)

        if last_status:
            return last_status
        raise TimeoutError(f"Processing timeout after {timeout} seconds")


async def check_services() -> Dict[str, bool]:
    """檢查服務狀態"""
    services_status = {
        "arangodb": False,
        "chromadb": False,
        "redis": False,
        "fastapi": False,
    }

    # 檢查FastAPI
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                services_status["fastapi"] = True
    except Exception:
        pass

    # 檢查ArangoDB（通過FastAPI）
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}{API_PREFIX}/health/arangodb")
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("status") == "healthy":
                    services_status["arangodb"] = True
    except Exception:
        pass

    # 檢查ChromaDB（通過FastAPI）
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}{API_PREFIX}/health/chromadb")
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("status") == "healthy":
                    services_status["chromadb"] = True
    except Exception:
        pass

    # 檢查Redis（通過FastAPI）
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{API_BASE_URL}{API_PREFIX}/health/redis")
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("status") == "healthy":
                    services_status["redis"] = True
    except Exception:
        pass

    return services_status


async def run_test(
    file_path: str, model: str = "ollama", user_id: str = TEST_USER_ID
) -> Dict[str, Any]:
    """執行測試"""
    logger.info("Starting test", file_path=file_path, model=model, user_id=user_id)

    # 檢查文件是否存在
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    file_size = os.path.getsize(file_path)
    logger.info("File info", path=file_path, size=file_size)

    # 檢查服務狀態
    logger.info("Checking services...")
    services_status = await check_services()
    logger.info("Services status", **services_status)

    if not all(services_status.values()):
        missing = [k for k, v in services_status.items() if not v]
        logger.warning("Some services are not available", missing=missing)

    # 記錄開始時間
    start_time = time.time()

    # 上傳文件
    logger.info("Uploading file...")
    upload_start = time.time()
    async with TestClient() as client:
        upload_result = await client.upload_file(file_path, user_id=user_id)
        upload_time = time.time() - upload_start

        if not upload_result.get("success"):
            raise RuntimeError(f"Upload failed: {upload_result.get('message')}")

        uploaded_files = upload_result.get("data", {}).get("uploaded", [])
        if not uploaded_files:
            raise RuntimeError("No files uploaded")

        file_id = uploaded_files[0].get("file_id")
        if not file_id:
            raise RuntimeError("File ID not found in upload response")

        logger.info("File uploaded", file_id=file_id, upload_time=upload_time)

        # 等待處理完成
        logger.info("Waiting for processing...")
        processing_start = time.time()
        status = await client.wait_for_processing(file_id, timeout=600)
        processing_time = time.time() - processing_start

        # 獲取詳細狀態
        final_status = await client.get_processing_status(file_id)
        status_data = final_status.get("data", {})

        # 獲取知識圖譜統計
        logger.info("Getting KG stats...")
        kg_stats_result = await client.get_kg_stats(file_id)
        kg_stats = kg_stats_result.get("data", {})

        # 獲取三元組列表
        logger.info("Getting KG triples...")
        triples_result = await client.get_kg_triples(file_id, limit=1000)
        triples_data = triples_result.get("data", {})

        # 構建測試結果
        result = {
            "test_info": {
                "file_path": file_path,
                "file_size": file_size,
                "model": model,
                "user_id": user_id,
                "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            },
            "upload": {
                "status": "success",
                "file_id": file_id,
                "upload_time": round(upload_time, 2),
            },
            "processing": {
                "status": status_data.get("status"),
                "progress": status_data.get("progress"),
                "processing_time": round(processing_time, 2),
                "chunking": status_data.get("chunking", {}),
                "vectorization": status_data.get("vectorization", {}),
                "storage": status_data.get("storage", {}),
                "kg_extraction": status_data.get("kg_extraction", {}),
            },
            "knowledge_graph": {
                "stats": kg_stats,
                "triples_count": triples_data.get("total", 0),
                "triples": triples_data.get("triples", [])[:10],  # 只保存前10個
            },
            "summary": {
                "total_time": round(time.time() - start_time, 2),
                "upload_time": round(upload_time, 2),
                "processing_time": round(processing_time, 2),
                "chunks_count": status_data.get("chunking", {}).get("chunk_count", 0),
                "entities_count": kg_stats.get("entities_count", 0),
                "relations_count": kg_stats.get("relations_count", 0),
                "entity_types": kg_stats.get("entity_types", []),
                "relation_types": kg_stats.get("relation_types", []),
            },
        }

        logger.info("Test completed", **result["summary"])

        return result


def main():
    """主函數"""
    parser = argparse.ArgumentParser(description="單一文件知識圖譜提取測試")
    parser.add_argument("--file", required=True, help="測試文件路徑")
    parser.add_argument("--model", default="ollama", choices=["ollama", "gemini"], help="模型類型")
    parser.add_argument("--user-id", default=TEST_USER_ID, help="用戶ID")
    parser.add_argument("--output", help="輸出JSON文件路徑")

    args = parser.parse_args()

    # 執行測試
    try:
        result = asyncio.run(run_test(args.file, args.model, args.user_id))

        # 輸出結果
        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"結果已保存到: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

        # 打印摘要
        print("\n" + "=" * 80)
        print("測試摘要")
        print("=" * 80)
        summary = result["summary"]
        print(f"文件: {result['test_info']['file_path']}")
        print(f"模型: {result['test_info']['model']}")
        print(f"總處理時間: {summary['total_time']} 秒")
        print(f"上傳時間: {summary['upload_time']} 秒")
        print(f"處理時間: {summary['processing_time']} 秒")
        print(f"分塊數量: {summary['chunks_count']}")
        print(f"實體數量: {summary['entities_count']}")
        print(f"關係數量: {summary['relations_count']}")
        print(f"實體類型: {', '.join(summary['entity_types'][:10])}")
        print(f"關係類型: {', '.join(summary['relation_types'][:10])}")

        sys.exit(0)
    except Exception as e:
        logger.error("Test failed", error=str(e))
        print(f"測試失敗: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
