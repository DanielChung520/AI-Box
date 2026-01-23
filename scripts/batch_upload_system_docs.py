#!/usr/bin/env python3
"""
系统设计文档批量上传脚本

功能：
- 扫描 docs/系统设计文档/ 下的所有文件
- 调用 POST /files/upload 上传文件（测试代码）
- 收集 file_ids
- 调用 POST /api/v1/rq/batch-upload 提交任务到 Worker（批量上传）

用法：
    python scripts/batch_upload_system_docs.py --test          # 测试模式（处理1个文件）
    python scripts/batch_upload_system_docs.py --limit 10      # 处理前10个文件
    python scripts/batch_upload_system_docs.py --all          # 处理所有文件
    python scripts/batch_upload_system_docs.py --status       # 查看当前状态
    python scripts/batch_upload_system_docs.py --submit       # 提交已上传文件到 Worker
    python scripts/batch_upload_system_docs.py --full         # 上传 + 提交到 Worker

环境变量：
    API_BASE_URL     API 地址 (默认: http://localhost:8000)
    API_TOKEN        API 认证 token
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiohttp
import structlog

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = structlog.get_logger()

DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs/系统设计文档")
PROGRESS_FILE = Path("/Users/daniel/GitHub/AI-Box/docs_progress.json")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/api/v1"
API_TOKEN = os.getenv("API_TOKEN", "")
TASK_ID = "systemAdmin_SystemDocs"


class BatchUploadSystemDocs:
    """系统设计文档批量上传器"""

    def __init__(self):
        self.docs_dir = DOCS_DIR
        self.progress_file = PROGRESS_FILE
        self.api_base_url = API_BASE_URL
        self.api_prefix = API_PREFIX
        self.api_token = API_TOKEN
        self.task_id = TASK_ID
        self.session: Optional[aiohttp.ClientSession] = None
        self.progress_data = self._load_progress()

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"
        return headers

    def _load_progress(self) -> List[Dict]:
        """加载进度表"""
        if self.progress_file.exists():
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_progress(self):
        """保存进度表"""
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress_data, f, ensure_ascii=False, indent=2)

    def scan_files(self) -> List[Dict[str, str]]:
        """扫描文档目录，生成文件列表"""
        files = []
        ignore_patterns = {".DS_Store", "__pycache__"}
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp"}

        for root, dirs, filenames in os.walk(self.docs_dir):
            for filename in filenames:
                if filename in ignore_patterns:
                    continue
                full_path = Path(root) / filename
                rel_path = full_path.relative_to(self.docs_dir)
                file_path = str(rel_path)

                ext = full_path.suffix.lower()
                is_image = ext in image_extensions

                files.append(
                    {
                        "file_path": file_path,
                        "full_path": str(full_path),
                        "is_image": is_image,
                    }
                )

        logger.info(f"Scanned {len(files)} files in {self.docs_dir}")
        return files

    def init_progress_file(self):
        """初始化进度表"""
        files = self.scan_files()

        for file_info in files:
            file_path = file_info["file_path"]
            if not any(f["文件路径"] == file_path for f in self.progress_data):
                self.progress_data.append(
                    {
                        "文件路径": file_path,
                        "状态": "pending",
                        "file_id": None,
                        "job_id": None,
                        "error": None,
                    }
                )

        self._save_progress()
        logger.info(f"Initialized progress file with {len(self.progress_data)} files")

    def get_file_type(self, filename: str) -> str:
        """根据文件名获取文件类型"""
        ext = Path(filename).suffix.lower()
        type_map = {
            ".md": "text/markdown",
            ".txt": "text/plain",
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".json": "application/json",
            ".html": "text/html",
        }
        return type_map.get(ext, "application/octet-stream")

    async def upload_file(self, file_info: Dict) -> Dict[str, Any]:
        """上传单个文件到 API"""
        file_path = file_info["file_path"]
        full_path = file_info["full_path"]

        try:
            with open(full_path, "rb") as f:
                file_content = f.read()

            file_type = self.get_file_type(Path(file_path).name)

            url = f"{self.api_base_url}{self.api_prefix}/files/upload?agent_id=system&task_id={self.task_id}"
            data = aiohttp.FormData()
            data.add_field(
                "file",  # 注意：使用 'file' 而不是 'files'
                file_content,
                filename=Path(file_path).name,
                content_type=file_type,
            )
            if self.task_id:
                data.add_field("task_id", self.task_id)

            headers = self._get_headers()
            async with self.session.post(url, data=data, headers=headers) as response:
                if response.status in [200, 207]:
                    result = await response.json()
                    if result.get("success"):
                        file_id = result.get("data", {}).get("file_id")
                        if file_id:
                            return {
                                "file_id": file_id,
                                "status": "uploaded",
                            }
                    return {
                        "status": "error",
                        "error": result.get("message", f"HTTP {response.status}"),
                    }
                else:
                    text = await response.text()
                    return {
                        "status": "error",
                        "error": f"HTTP {response.status}: {text[:200]}",
                    }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def submit_to_worker(self, file_ids: List[str]) -> Dict[str, Any]:
        """提交文件到 Worker 队列处理"""
        try:
            url = f"{self.api_base_url}{self.api_prefix}/rq/batch-upload"
            payload = {
                "file_ids": file_ids,
                "task_id": self.task_id,
                "options": {
                    "rechunk": False,
                    "vectorize": True,
                    "extract_kg": True,
                },
            }

            headers = self._get_headers()
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("data", {})
                else:
                    text = await response.text()
                    return {"error": f"HTTP {response.status}: {text[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    async def run_upload(self, limit: Optional[int] = None, test: bool = False):
        """运行上传流程"""
        await self._ensure_session()

        pending_files = [f for f in self.progress_data if f["状态"] == "pending"]

        if test:
            files_to_process = pending_files[:1]
            logger.info("TEST mode - uploading 1 file")
        elif limit:
            files_to_process = pending_files[:limit]
            logger.info(f"Processing first {limit} files")
        else:
            files_to_process = pending_files
            logger.info(f"Processing all {len(pending_files)} pending files")

        success_count = 0
        error_count = 0
        uploaded_ids = []

        for idx, file_info in enumerate(files_to_process, 1):
            file_path = file_info["文件路径"]
            file_record = next((f for f in self.progress_data if f["文件路径"] == file_path), None)

            logger.info(f"[{idx}/{len(files_to_process)}] Uploading: {file_path}")

            scan_info = {"file_path": file_path, "full_path": str(self.docs_dir / file_path)}
            result = await self.upload_file(scan_info)

            if result.get("status") == "uploaded":
                file_record["状态"] = "uploaded"
                file_record["file_id"] = result["file_id"]
                uploaded_ids.append(result["file_id"])
                success_count += 1
                logger.info(f"  -> Uploaded, file_id: {result['file_id']}")
            else:
                file_record["状态"] = "error"
                file_record["error"] = result.get("error", "Unknown error")
                error_count += 1
                logger.error(f"  -> Failed: {result.get('error')}")

            self._save_progress()
            await asyncio.sleep(0.3)

        await self._close_session()

        logger.info(f"Upload completed: {success_count} success, {error_count} errors")
        return {"success": success_count, "errors": error_count, "uploaded_ids": uploaded_ids}

    async def run_submit(self, limit: Optional[int] = None, test: bool = False):
        """提交已上传文件到 Worker"""
        await self._ensure_session()

        uploaded_files = [f for f in self.progress_data if f["状态"] == "uploaded"]

        if test:
            files_to_submit = uploaded_files[:1]
            logger.info("TEST mode - submitting 1 file to worker")
        elif limit:
            files_to_submit = uploaded_files[:limit]
            logger.info(f"Submitting first {limit} files")
        else:
            files_to_submit = uploaded_files
            logger.info(f"Submitting all {len(uploaded_files)} uploaded files")

        file_ids = [f["file_id"] for f in files_to_submit if f.get("file_id")]

        if not file_ids:
            logger.warning("No uploaded files to submit")
            await self._close_session()
            return {"submitted": 0, "errors": 0}

        result = await self.submit_to_worker(file_ids)
        submitted = result.get("submitted", 0)
        failed = result.get("failed", 0)

        if submitted > 0:
            for idx, file_info in enumerate(files_to_submit):
                if idx < len(result.get("results", [])):
                    r = result["results"][idx]
                    if r.get("status") == "queued":
                        file_info["状态"] = "queued"
                        file_info["job_id"] = r.get("job_id")
            self._save_progress()

        logger.info(f"Submit completed: {submitted} submitted, {failed} failed")
        await self._close_session()
        return result

    async def run_full(self, limit: Optional[int] = None, test: bool = False):
        """完整流程：上传 + 提交到 Worker"""
        logger.info("=" * 60)
        logger.info("Starting FULL upload pipeline: upload + submit to worker")
        logger.info("=" * 60)

        upload_result = await self.run_upload(limit=limit, test=test)
        uploaded_ids = upload_result.get("uploaded_ids", [])

        if uploaded_ids:
            logger.info("-" * 60)
            submit_result = await self.run_submit(limit=len(uploaded_ids), test=False)
            return {"upload": upload_result, "submit": submit_result}

        return {"upload": upload_result, "submit": {"submitted": 0, "failed": 0}}

    async def _ensure_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def _close_session(self):
        if self.session:
            await self.session.close()
            self.session = None

    def show_status(self):
        """显示当前状态"""
        total = len(self.progress_data)
        if total == 0:
            print("\n=== 系统设计文档批量上传进度 ===")
            print("进度表为空，请先运行 --init 初始化")
            return

        status_count = {}
        for f in self.progress_data:
            status = f["状态"]
            status_count[status] = status_count.get(status, 0) + 1

        print("\n=== 系统设计文档批量上传进度 ===")
        print(f"总文件数: {total}")
        print("\n状态统计:")
        for status, count in sorted(status_count.items()):
            print(f"  {status}: {count} 个")

        pending = status_count.get("pending", 0)
        uploaded = status_count.get("uploaded", 0)
        queued = status_count.get("queued", 0)
        error = status_count.get("error", 0)

        print("\n进度:")
        print(f"  待上传: {pending}")
        print(f"  已上传: {uploaded}")
        print(f"  已入队: {queued}")
        print(f"  错误: {error}")
        print(f"  完成率: {(total - pending) / total * 100:.1f}%")


async def main():
    parser = argparse.ArgumentParser(description="系统设计文档批量上传脚本")
    parser.add_argument("--test", action="store_true", help="测试模式（处理1个文件）")
    parser.add_argument("--limit", type=int, default=None, help="限制处理文件数量")
    parser.add_argument("--all", action="store_true", help="处理所有文件")
    parser.add_argument("--status", action="store_true", help="显示当前状态")
    parser.add_argument("--init", action="store_true", help="初始化进度表（扫描文件）")
    parser.add_argument("--submit", action="store_true", help="提交已上传文件到 Worker")
    parser.add_argument("--full", action="store_true", help="上传 + 提交到 Worker")

    args = parser.parse_args()

    processor = BatchUploadSystemDocs()

    if args.status:
        processor.show_status()
    elif args.init:
        processor.init_progress_file()
        processor.show_status()
    elif args.test:
        if args.full:
            result = await processor.run_full(test=True)
        elif args.submit:
            result = await processor.run_submit(test=True)
        else:
            result = await processor.run_upload(test=True)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.limit:
        if args.full:
            result = await processor.run_full(limit=args.limit)
        elif args.submit:
            result = await processor.run_submit(limit=args.limit)
        else:
            result = await processor.run_upload(limit=args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.all:
        if args.full:
            result = await processor.run_full()
        elif args.submit:
            result = await processor.run_submit()
        else:
            result = await processor.run_upload()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.full:
        result = await processor.run_full()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.submit:
        result = await processor.run_submit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
