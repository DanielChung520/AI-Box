#!/usr/bin/env python3
"""
系统设计文档批量上传脚本

功能：
- 将系统设计文档批量上传到 SeaWeedFS
- 处理向量化存储到 ChromaDB
- 提取知识图谱存储到 ArangoDB
- 更新进度管制表

用法：
    python scripts/migration/batch_upload_docs.py --test          # 测试模式（处理1个文件）
    python scripts/migration/batch_upload_docs.py --limit 10      # 处理前10个文件
    python scripts/migration/batch_upload_docs.py --all          # 处理所有文件
    python scripts/migration/batch_upload_docs.py --status       # 查看当前状态
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import structlog
from arango.client import ArangoClient

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = structlog.get_logger(__name__)

# 配置
DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs/系统设计文档")
PROGRESS_FILE = Path("/Users/daniel/GitHub/AI-Box/docs_progress.json")
TASK_ID = "systemAdmin_SystemDocs"

# ArangoDB 配置
ARANGODB_HOST = os.getenv("ARANGODB_HOST", "localhost")
ARANGODB_PORT = int(os.getenv("ARANGODB_PORT", "8529"))
ARANGODB_DB = "ai_box_kg"
ARANGODB_USER = os.getenv("ARANGODB_USERNAME", "root")
ARANGODB_PASS = os.getenv("ARANGODB_PASSWORD", "changeme")


class BatchDocProcessor:
    """批量文档处理器"""

    def __init__(self):
        self.docs_dir = DOCS_DIR
        self.progress_file = PROGRESS_FILE
        self.task_id = TASK_ID

        # 加载进度表
        self.progress_data = self._load_progress()

        # 初始化 ArangoDB
        self._init_arangodb()

        # 初始化存储
        self._init_storage()

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

    def _init_arangodb(self):
        """初始化 ArangoDB 连接"""
        self.arango_client = ArangoClient(hosts=f"http://{ARANGODB_HOST}:{ARANGODB_PORT}")
        self.db = self.arango_client.db(ARANGODB_DB, username=ARANGODB_USER, password=ARANGODB_PASS)
        logger.info("ArangoDB connected", database=ARANGODB_DB)

    def _init_storage(self):
        """初始化文件存储"""
        from storage.file_storage import create_storage_from_config

        config = {
            "storage_backend": "s3",
            "service_type": "ai_box",
            "ai_box_seaweedfs_s3_endpoint": os.getenv(
                "AI_BOX_SEAWEEDFS_S3_ENDPOINT", "http://localhost:8333"
            ),
            "ai_box_seaweedfs_s3_access_key": os.getenv("AI_BOX_SEAWEEDFS_S3_ACCESS_KEY", "admin"),
            "ai_box_seaweedfs_s3_secret_key": os.getenv(
                "AI_BOX_SEAWEEDFS_S3_SECRET_KEY", "admin123"
            ),
            "ai_box_seaweedfs_use_ssl": False,
        }
        self.storage = create_storage_from_config(config)
        logger.info("Storage initialized", backend="s3")

    def get_file_id(self, file_path: str) -> str:
        """生成文件 ID"""
        content = (self.docs_dir / file_path).read_bytes()
        return hashlib.md5(content).hexdigest()

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

    def update_progress(self, file_path: str, status: str, **kwargs):
        """更新进度"""
        for item in self.progress_data:
            if item["文件路径"] == file_path:
                item["状态"] = status
                for k, v in kwargs.items():
                    item[k] = v
                break
        self._save_progress()

    def upload_file(self, file_path: str) -> Dict[str, Any]:
        """上传单个文件"""
        full_path = self.docs_dir / file_path
        if not full_path.exists():
            raise FileNotFoundError(f"文件不存在: {full_path}")

        file_id = self.get_file_id(file_path)
        file_type = self.get_file_type(full_path.name)

        # 读取文件内容
        with open(full_path, "rb") as f:
            content = f.read()

        logger.info("Uploading file", file_path=file_path, file_id=file_id)

        # 上传到 SeaWeedFS
        # save_file 返回 (file_id, s3_uri) tuple
        save_result = self.storage.save_file(
            file_content=content, filename=full_path.name, task_id=self.task_id
        )

        # 处理 tuple 返回值
        if isinstance(save_result, tuple):
            upload_file_id, s3_uri = save_result
            storage_path = f"tasks/{self.task_id}/{upload_file_id}"
        else:
            upload_file_id = save_result
            s3_uri = f"s3://bucket-ai-box-assets/tasks/{self.task_id}/{upload_file_id}"
            storage_path = f"tasks/{self.task_id}/{upload_file_id}"

        return {
            "file_id": upload_file_id,
            "s3_uri": s3_uri,
            "storage_path": storage_path,
            "size": len(content),
        }

    def save_metadata_to_arangodb(self, file_path: str, upload_result: Dict):
        """保存元数据到 ArangoDB"""
        full_path = self.docs_dir / file_path

        # 确保 collection 存在
        if not self.db.has_collection("file_metadata"):
            self.db.create_collection("file_metadata")

        file_metadata = self.db.collection("file_metadata")

        doc = {
            "_key": upload_result["file_id"],
            "filename": full_path.name,
            "file_type": self.get_file_type(full_path.name),
            "file_size": upload_result["size"],
            "task_id": self.task_id,
            "storage_path": upload_result["storage_path"],
            "s3_uri": upload_result.get("s3_uri"),
            "status": "uploaded",
            "source": "system_docs_batch",
            "created_at": datetime.now().isoformat(),
        }

        file_metadata.insert(doc)
        logger.info("Metadata saved to ArangoDB", file_id=upload_result["file_id"])

        return doc

    def process_file(self, file_path: str) -> Dict[str, Any]:
        """处理单个文件"""
        result = {"file_path": file_path, "status": "error", "error": None}

        try:
            # 1. 上传到 SeaWeedFS
            self.update_progress(file_path, "uploading")
            upload_result = self.upload_file(file_path)

            # 2. 保存元数据到 ArangoDB
            self.update_progress(file_path, "metadata")
            self.save_metadata_to_arangodb(file_path, upload_result)

            result["file_id"] = upload_result["file_id"]
            result["s3_uri"] = upload_result["s3_uri"]
            result["status"] = "uploaded"

            logger.info(
                "File processed successfully", file_path=file_path, file_id=upload_result["file_id"]
            )

        except Exception as e:
            result["error"] = str(e)
            logger.error("File processing failed", file_path=file_path, error=str(e))

        return result

    def run(self, limit: Optional[int] = None, test: bool = False):
        """运行批量处理"""
        # 筛选 pending 状态的文件
        pending_files = [f for f in self.progress_data if f["状态"] == "pending"]

        if test:
            # 测试模式：只处理 1 个文件
            files_to_process = pending_files[:1]
            logger.info("Running in TEST mode - processing 1 file")
        elif limit:
            files_to_process = pending_files[:limit]
            logger.info(f"Processing first {limit} files")
        else:
            files_to_process = pending_files
            logger.info(f"Processing all {len(pending_files)} pending files")

        success_count = 0
        error_count = 0

        for idx, file_info in enumerate(files_to_process, 1):
            file_path = file_info["文件路径"]

            logger.info(f"Processing [{idx}/{len(files_to_process)}]: {file_path}")

            result = self.process_file(file_path)

            if result["status"] == "uploaded":
                self.update_progress(
                    file_path, "uploaded", file_id=result["file_id"], s3_uri=result["s3_uri"]
                )
                success_count += 1
            else:
                self.update_progress(file_path, "error", error=result["error"])
                error_count += 1

            # 保存进度
            self._save_progress()

            # 短暂延迟避免过载
            time.sleep(0.5)

        logger.info(
            "Batch processing completed",
            total=len(files_to_process),
            success=success_count,
            errors=error_count,
        )

        return {"success": success_count, "errors": error_count}

    def show_status(self):
        """显示当前状态"""
        total = len(self.progress_data)
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
        print(f"\n进度: {(total - pending) / total * 100:.1f}%")

        # 显示最近的错误
        errors = [f for f in self.progress_data if f["状态"] == "error"]
        if errors:
            print("\n最近的错误:")
            for f in errors[:5]:
                print(f"  - {f['文件路径']}: {f.get('error', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(description="系统设计文档批量上传脚本")
    parser.add_argument("--test", action="store_true", help="测试模式（处理1个文件）")
    parser.add_argument("--limit", type=int, default=None, help="限制处理文件数量")
    parser.add_argument("--all", action="store_true", help="处理所有文件")
    parser.add_argument("--status", action="store_true", help="显示当前状态")

    args = parser.parse_args()

    processor = BatchDocProcessor()

    if args.status:
        processor.show_status()
    elif args.test:
        processor.run(test=True)
    elif args.limit:
        processor.run(limit=args.limit)
    elif args.all:
        processor.run()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
