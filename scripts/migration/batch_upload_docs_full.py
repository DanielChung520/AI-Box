#!/usr/bin/env python3
"""
系统设计文档完整處理腳本

功能：
1. 將系統設計文檔上傳到 SeaWeedFS
2. 執行文件分塊和向量化（存儲到 ChromaDB）
3. 執行知識圖譜提取（存儲到 ArangoDB）
4. 更新進度管制表

用法：
    python scripts/migration/batch_upload_docs_full.py --test          # 測試模式（處理1個文件）
    python scripts/migration/batch_upload_docs_full.py --limit 10      # 處理前10個文件
    python scripts/migration/batch_upload_docs_full.py --all          # 處理所有文件
    python scripts/migration/batch_upload_docs_full.py --status       # 查看當前狀態
"""

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加項目根目錄到路徑
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import structlog
from arango.client import ArangoClient

# 配置日誌
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = structlog.get_logger(__name__)

# 配置
DOCS_DIR = Path("/Users/daniel/GitHub/AI-Box/docs/系统设计文档")
PROGRESS_FILE = Path("/Users/daniel/GitHub/AI-Box/docs_progress.json")
TASK_ID = "systemAdmin_SystemDocs"
USER_ID = "system_admin"

# ArangoDB 配置
ARANGODB_HOST = os.getenv("ARANGODB_HOST", "localhost")
ARANGODB_PORT = int(os.getenv("ARANGODB_PORT", "8529"))
ARANGODB_DB = "ai_box_kg"
ARANGODB_USER = os.getenv("ARANGODB_USERNAME", "root")
ARANGODB_PASS = os.getenv("ARANGODB_PASSWORD", "changeme")


class FullDocProcessor:
    """完整文檔處理器 - 處理上傳、向量化、圖譜化"""

    def __init__(self):
        self.docs_dir = DOCS_DIR
        self.progress_file = PROGRESS_FILE
        self.task_id = TASK_ID
        self.user_id = USER_ID

        # 加載進度表
        self.progress_data = self._load_progress()

        # 初始化 ArangoDB
        self._init_arangodb()

        # 初始化存儲
        self._init_storage()

    def _load_progress(self) -> List[Dict]:
        """加載進度表"""
        if self.progress_file.exists():
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _save_progress(self):
        """保存進度表"""
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.progress_data, f, ensure_ascii=False, indent=2)

    def _init_arangodb(self):
        """初始化 ArangoDB 連接"""
        self.arango_client = ArangoClient(hosts=f"http://{ARANGODB_HOST}:{ARANGODB_PORT}")
        self.db = self.arango_client.db(ARANGODB_DB, username=ARANGODB_USER, password=ARANGODB_PASS)
        logger.info("ArangoDB connected", database=ARANGODB_DB)

    def _init_storage(self):
        """初始化文件存儲"""
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
        """根據文件名獲取文件類型"""
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
        """更新進度"""
        for item in self.progress_data:
            if item["文件路径"] == file_path:
                item["状态"] = status
                for k, v in kwargs.items():
                    item[k] = v
                break
        self._save_progress()

    def ensure_task_exists(self):
        """確保任務存在"""
        tasks = self.db.collection("user_tasks")
        if not tasks.has("systemAdmin_SystemDocs"):
            task_doc = {
                "_key": "systemAdmin_SystemDocs",
                "task_id": "systemAdmin_SystemDocs",
                "user_id": "system",
                "title": "SystemDocs",
                "status": "active",
                "task_status": "processing",
                "created_at": datetime.now().isoformat(),
            }
            tasks.insert(task_doc)
            logger.info("Created task: systemAdmin_SystemDocs")

    def save_metadata_to_arangodb(
        self, file_path: str, upload_result: Dict, chunks_count: int = 0, vectors_count: int = 0
    ):
        """保存元數據到 ArangoDB"""
        full_path = self.docs_dir / file_path

        # 確保 collection 存在
        if not self.db.has_collection("file_metadata"):
            self.db.create_collection("file_metadata")

        file_metadata = self.db.collection("file_metadata")

        doc = {
            "_key": upload_result["file_id"],
            "filename": full_path.name,
            "file_type": self.get_file_type(full_path.name),
            "file_size": upload_result["size"],
            "task_id": self.task_id,
            "user_id": self.user_id,
            "storage_path": upload_result["storage_path"],
            "s3_uri": upload_result.get("s3_uri"),
            "status": "processed",
            "chunk_count": chunks_count,
            "vector_count": vectors_count,
            "source": "system_docs_full_batch",
            "created_at": datetime.now().isoformat(),
        }

        file_metadata.insert(doc)
        logger.info("Metadata saved to ArangoDB", file_id=upload_result["file_id"])

        return doc

    async def process_vectorization(self, file_id: str, file_path: str, file_type: str):
        """執行向量化處理"""
        try:
            # 動態導入避免循環依賴
            from api.routers.file_upload import process_file_chunking_and_vectorization

            logger.info("Starting vectorization", file_id=file_id, file_path=file_path)

            result = await process_file_chunking_and_vectorization(
                file_id=file_id, file_path=file_path, file_type=file_type, user_id=self.user_id
            )

            logger.info("Vectorization completed", file_id=file_id)
            return result

        except Exception as e:
            logger.error("Vectorization failed", file_id=file_id, error=str(e))
            raise

    async def process_kg_extraction(self, file_id: str, file_path: str, file_type: str):
        """執行知識圖譜提取"""
        try:
            from api.routers.file_upload import process_kg_extraction_only

            logger.info("Starting KG extraction", file_id=file_id, file_path=file_path)

            result = await process_kg_extraction_only(
                file_id=file_id,
                file_path=file_path,
                file_type=file_type,
                user_id=self.user_id,
                force_rechunk=False,
            )

            logger.info("KG extraction completed", file_id=file_id)
            return result

        except Exception as e:
            logger.error("KG extraction failed", file_id=file_id, error=str(e))
            raise

    async def process_single_file(self, file_path: str) -> Dict[str, Any]:
        """完整處理單個文件：上傳 + 向量化 + 知識圖譜"""
        result = {"file_path": file_path, "status": "error", "error": None, "steps": {}}

        full_path = self.docs_dir / file_path
        if not full_path.exists():
            result["error"] = f"文件不存在: {full_path}"
            return result

        file_type = self.get_file_type(full_path.name)

        try:
            # === 步驟 1: 上傳到 SeaWeedFS ===
            self.update_progress(file_path, "uploading")
            logger.info(f"Step 1/3: Uploading {file_path}")

            with open(full_path, "rb") as f:
                content = f.read()

            save_result = self.storage.save_file(
                file_content=content, filename=full_path.name, task_id=self.task_id
            )

            if isinstance(save_result, tuple):
                upload_file_id, s3_uri = save_result
                storage_path = f"tasks/{self.task_id}/{upload_file_id}"
            else:
                upload_file_id = save_result
                s3_uri = f"s3://bucket-ai-box-assets/tasks/{self.task_id}/{upload_file_id}"
                storage_path = f"tasks/{self.task_id}/{upload_file_id}"

            upload_result = {
                "file_id": upload_file_id,
                "s3_uri": s3_uri,
                "storage_path": storage_path,
                "size": len(content),
            }

            result["steps"]["upload"] = {
                "status": "success",
                "file_id": upload_file_id,
                "s3_uri": s3_uri,
            }

            # === 步驟 2: 向量化 (ChromaDB) ===
            self.update_progress(file_path, "vectorizing")
            logger.info(f"Step 2/3: Vectorizing {file_path}")

            # 使用文件系統路徑進行向量化
            vectorization_result = await self.process_vectorization(
                file_id=upload_file_id,
                file_path=str(full_path),  # 使用實際檔案路徑
                file_type=file_type,
            )

            chunks_count = (
                vectorization_result.get("total_chunks", 0) if vectorization_result else 0
            )
            vectors_count = (
                vectorization_result.get("vector_count", 0) if vectorization_result else 0
            )

            result["steps"]["vectorization"] = {
                "status": "success",
                "chunks": chunks_count,
                "vectors": vectors_count,
            }

            # === 步驟 3: 知識圖譜 (ArangoDB) ===
            self.update_progress(file_path, "kg_extracting")
            logger.info(f"Step 3/3: Extracting KG for {file_path}")

            kg_result = await self.process_kg_extraction(
                file_id=upload_file_id, file_path=str(full_path), file_type=file_type
            )

            entities_count = kg_result.get("entities_created", 0) if kg_result else 0
            relations_count = kg_result.get("relations_created", 0) if kg_result else 0

            result["steps"]["kg_extraction"] = {
                "status": "success",
                "entities": entities_count,
                "relations": relations_count,
            }

            # === 保存元數據 ===
            self.update_progress(file_path, "saving_metadata")
            self.ensure_task_exists()
            self.save_metadata_to_arangodb(
                file_path, upload_result, chunks_count=chunks_count, vectors_count=vectors_count
            )

            result["status"] = "processed"
            result["file_id"] = upload_file_id
            result["s3_uri"] = s3_uri

            logger.info(f"File processed successfully: {file_path}")
            logger.info(f"  - Uploaded: {upload_file_id}")
            logger.info(f"  - Vectors: {vectors_count}")
            logger.info(f"  - Entities: {entities_count}")
            logger.info(f"  - Relations: {relations_count}")

        except Exception as e:
            result["error"] = str(e)
            logger.error(f"File processing failed: {file_path}", error=str(e))

        return result

    def run(self, limit: Optional[int] = None, test: bool = False):
        """運行批量處理"""
        # 篩選 pending 狀態的文件
        pending_files = [f for f in self.progress_data if f["状态"] == "pending"]

        if test:
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

            logger.info(f"\n{'=' * 60}")
            logger.info(f"[{idx}/{len(files_to_process)}] Processing: {file_path}")
            logger.info(f"{'=' * 60}")

            result = asyncio.run(self.process_single_file(file_path))

            if result["status"] == "processed":
                self.update_progress(
                    file_path,
                    "processed",
                    file_id=result["file_id"],
                    s3_uri=result["s3_uri"],
                    chunks=result["steps"]["vectorization"].get("chunks", 0),
                    vectors=result["steps"]["vectorization"].get("vectors", 0),
                    entities=result["steps"]["kg_extraction"].get("entities", 0),
                    relations=result["steps"]["kg_extraction"].get("relations", 0),
                )
                success_count += 1
            else:
                self.update_progress(file_path, "error", error=result["error"])
                error_count += 1

            # 保存進度
            self._save_progress()

            # 短暫延遲避免過載
            time.sleep(1)

        logger.info(f"\n{'=' * 60}")
        logger.info("Batch processing completed")
        logger.info(
            f"Total: {len(files_to_process)}, Success: {success_count}, Errors: {error_count}"
        )
        logger.info(f"{'=' * 60}")

        return {"success": success_count, "errors": error_count}

    def show_status(self):
        """顯示當前狀態"""
        total = len(self.progress_data)
        status_count = {}
        for f in self.progress_data:
            status = f["状态"]
            status_count[status] = status_count.get(status, 0) + 1

        print(f"\n{'=' * 60}")
        print("系統設計文檔批量處理進度")
        print(f"{'=' * 60}")
        print(f"總文件數: {total}")
        print("\n狀態統計:")
        for status, count in sorted(status_count.items()):
            print(f"  {status}: {count} 個")

        pending = status_count.get("pending", 0)
        processed = status_count.get("processed", 0)
        print(f"\n進度: {processed}/{total} ({processed / total * 100:.1f}%)")

        # 顯示處理成功的文件統計
        if processed > 0:
            total_chunks = sum(
                f.get("chunks", 0) for f in self.progress_data if f["状态"] == "processed"
            )
            total_vectors = sum(
                f.get("vectors", 0) for f in self.progress_data if f["状态"] == "processed"
            )
            total_entities = sum(
                f.get("entities", 0) for f in self.progress_data if f["状态"] == "processed"
            )
            total_relations = sum(
                f.get("relations", 0) for f in self.progress_data if f["状态"] == "processed"
            )
            print("\n處理統計:")
            print(f"  總 Chunks: {total_chunks}")
            print(f"  總 Vectors: {total_vectors}")
            print(f"  總 Entities: {total_entities}")
            print(f"  總 Relations: {total_relations}")

        # 顯示最近的錯誤
        errors = [f for f in self.progress_data if f["状态"] == "error"]
        if errors:
            print("\n最近的錯誤:")
            for f in errors[:5]:
                print(f"  - {f['文件路径']}: {f.get('error', 'Unknown')}")

        print(f"{'=' * 60}")


def main():
    parser = argparse.ArgumentParser(description="系統設計文檔完整處理腳本")
    parser.add_argument("--test", action="store_true", help="測試模式（處理1個文件）")
    parser.add_argument("--limit", type=int, default=None, help="限制處理文件數量")
    parser.add_argument("--all", action="store_true", help="處理所有文件")
    parser.add_argument("--status", action="store_true", help="顯示當前狀態")

    args = parser.parse_args()

    processor = FullDocProcessor()

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
