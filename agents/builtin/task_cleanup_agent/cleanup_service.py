# 代碼功能說明: Task Cleanup Agent 核心服務類
# 創建日期: 2026-01-23 10:35 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-23 10:35 UTC+8

import os
import base64
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import httpx
from arango.client import ArangoClient
from qdrant_client import QdrantClient
from dotenv import load_dotenv

from agents.builtin.task_cleanup_agent.models import CleanupStats

logger = logging.getLogger(__name__)


class CleanupService:
    def __init__(self):
        # 顯式加載 .env
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        env_path = base_dir / ".env"
        load_dotenv(dotenv_path=env_path)

        self.arango_host = os.getenv("ARANGO_HOST", "http://localhost:8529")
        self.arango_db_name = os.getenv("ARANGO_DB", "ai_box_kg")
        self.arango_user = os.getenv("ARANGO_USERNAME", "root")
        self.arango_pwd = os.getenv("ARANGO_PASSWORD", "changeme")

        self.qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        self.qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

        self.seaweedfs_host = os.getenv("SEAWEEDFS_HOST", "localhost")
        self.seaweedfs_port = int(os.getenv("SEAWEEDFS_PORT", "8888"))
        self.seaweedfs_bucket = os.getenv("SEAWEEDFS_BUCKET", "bucket-ai-box-assets")
        self.seaweedfs_access_key = os.getenv("SEAWEEDFS_ACCESS_KEY", "admin")
        self.seaweedfs_secret_key = os.getenv("SEAWEEDFS_SECRET_KEY", "admin123")

    def _get_arango_db(self):
        client = ArangoClient(hosts=self.arango_host)
        return client.db(self.arango_db_name, username=self.arango_user, password=self.arango_pwd)

    def scan_data(self, user_id: str, task_id: Optional[str] = None) -> CleanupStats:
        """掃描待刪除數據統計"""
        stats = CleanupStats()
        db = self._get_arango_db()

        # 1. Tasks
        if task_id:
            aql = "FOR t IN user_tasks FILTER t.user_id == @user_id AND t.task_id == @task_id RETURN t.task_id"
            params: Dict[str, Any] = {"user_id": user_id, "task_id": task_id} 
        else:
            aql = "FOR t IN user_tasks FILTER t.user_id == @user_id RETURN t.task_id"
            params = {"user_id": user_id}

        task_ids = list(db.aql.execute(aql, bind_vars=params))
        stats.user_tasks = len(task_ids)

        # 2. Files
        if task_id:
            aql = "FOR f IN file_metadata FILTER f.user_id == @user_id AND f.task_id == @task_id RETURN f.file_id"
        else:
            aql = "FOR f IN file_metadata FILTER f.user_id == @user_id RETURN f.file_id"

        file_ids = list(db.aql.execute(aql, bind_vars=params))
        stats.file_metadata = len(file_ids)

        # 3. Entities & Relations (通過 file_id 關聯)
        if file_ids:
            for coll in ["entities", "relations"]:
                aql = f"FOR d IN {coll} FILTER d.file_id IN @file_ids RETURN d._key"
                cursor = db.aql.execute(aql, bind_vars={"file_ids": file_ids})
                count = len(list(cursor))
                if coll == "entities":
                    stats.entities = count
                else:
                    stats.relations = count

        stats.qdrant_collections = len(file_ids)
        stats.seaweedfs_directories = len(task_ids)

        return stats

    def execute_cleanup(self, user_id: str, task_id: Optional[str] = None) -> CleanupStats:
        """執行正式清理"""
        db = self._get_arango_db()
        stats = CleanupStats()

        # 先獲取 ID 清單
        if task_id:
            params: Dict[str, Any] = {"user_id": user_id, "task_id": task_id}
            task_ids = list(
                db.aql.execute(
                    "FOR t IN user_tasks FILTER t.user_id == @user_id AND t.task_id == @task_id RETURN t.task_id",
                    bind_vars=params,
                )
            )
            file_ids = list(
                db.aql.execute(
                    "FOR f IN file_metadata FILTER f.user_id == @user_id AND f.task_id == @task_id RETURN f.file_id",
                    bind_vars=params,
                )
            ),
        else:
            params = {"user_id": user_id}
            task_ids = list(
                db.aql.execute(
                    "FOR t IN user_tasks FILTER t.user_id == @user_id RETURN t.task_id",
                    bind_vars=params,
                )
            )
            file_ids = list(
                db.aql.execute(
                    "FOR f IN file_metadata FILTER f.user_id == @user_id RETURN f.file_id",
                    bind_vars=params,
                )
            )

        # 1. ArangoDB Entities & Relations
        if file_ids:
            for coll in ["entities", "relations"]:
                aql = f"FOR d IN {coll} FILTER d.file_id IN @file_ids REMOVE d IN {coll}"
                cursor = db.aql.execute(aql, bind_vars={"file_ids": file_ids})
                # 在 python-arango 中，execute 返回的是 cursor，如果是 REMOVE 類型的 AQL，
                # statistics 會在 cursor 遍歷完後或直接可用
                stats_info = cursor.statistics()
                count = stats_info.get("writesExecuted", 0) if stats_info else 0
                if coll == "entities":
                    stats.entities = count
                else:
                    stats.relations = count

        # 2. ArangoDB Metadata
        if file_ids:
            aql = "FOR f IN file_metadata FILTER f.file_id IN @file_ids REMOVE f IN file_metadata"
            cursor = db.aql.execute(aql, bind_vars={"file_ids": file_ids})
            stats_info = cursor.statistics()
            stats.file_metadata = stats_info.get("writesExecuted", 0) if stats_info else 0

        if task_ids:
            aql = "FOR t IN user_tasks FILTER t.task_id IN @task_ids REMOVE t IN user_tasks"
            cursor = db.aql.execute(aql, bind_vars={"task_ids": task_ids})
            stats_info = cursor.statistics()
            stats.user_tasks = stats_info.get("writesExecuted", 0) if stats_info else 0

        # 3. Qdrant
        if file_ids:
            try:
                q_client = QdrantClient(host=self.qdrant_host, port=self.qdrant_port)
                for fid in file_ids:
                    try:
                        q_client.delete_collection(f"file_{fid}")
                        stats.qdrant_collections += 1
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Qdrant cleanup error: {e}")

        # 4. SeaweedFS
        if task_ids:
            filer_url = f"http://{self.seaweedfs_host}:{self.seaweedfs_port}"
            auth = (
                "Basic "
                + base64.b64encode(
                    f"{self.seaweedfs_access_key}:{self.seaweedfs_secret_key}".encode()
                ).decode()
            )
            for tid in task_ids:
                try:
                    url = f"{filer_url}/{self.seaweedfs_bucket}/tasks/{tid}/?recursive=true"
                    resp = httpx.delete(url, headers={"Authorization": auth})
                    if resp.status_code in [200, 204, 404]:
                        stats.seaweedfs_directories += 1
                except Exception as e:
                    logger.error(f"SeaweedFS cleanup error: {e}")

        return stats