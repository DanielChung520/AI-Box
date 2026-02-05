# 代碼功能說明: Task Cleanup Agent 審計日誌服務 (AOGA 合規)
# 創建日期: 2026-01-23
# 創建人: Daniel Chung

import json
import hashlib
import logging
from datetime import datetime
from typing import Any, Dict

from database.arangodb import ArangoDBClient
from agents.builtin.task_cleanup_agent.models import AOGAAuditRecord

logger = logging.getLogger(__name__)

SYSTEM_AUDIT_LOG_COLLECTION = "system_audit_logs"


class AOGAAuditLogger:
    """符合 AOGA 架構的審計日誌記錄器"""
    def __init__(self):
        self.client = ArangoDBClient()
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        if not self.client.db.has_collection(SYSTEM_AUDIT_LOG_COLLECTION):
            self.client.db.create_collection(SYSTEM_AUDIT_LOG_COLLECTION)
            coll = self.client.db.collection(SYSTEM_AUDIT_LOG_COLLECTION)
            coll.add_index({"type": "persistent", "fields": ["actor"]})
            coll.add_index({"type": "persistent", "fields": ["action_type"]})
            coll.add_index({"type": "persistent", "fields": ["timestamp"]})

    def _calculate_hash(self, record_dict: Dict[str, Any]) -> str:
        """計算記錄的 SHA-256 哈希值以確保不可篡改性"""
        # 排除 content_hash 本身和 ArangoDB 內部欄位
        excluded = ["content_hash", "_id", "_rev"]
        data_to_hash = {k: v for k, v in record_dict.items() if k not in excluded}
        # 排序 key 以確保哈希穩定
        serialized = json.dumps(data_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode()).hexdigest()

    async def record(self, record: AOGAAuditRecord) -> str:
        """記錄審計日誌並返回記錄 ID"""
        try:
            record_dict = record.model_dump()
            # ArangoDB 鍵值對應
            record_dict["_key"] = record.record_id

            # 計算並注入內容雜湊
            record_dict["content_hash"] = self._calculate_hash(record_dict)

            coll = self.client.db.collection(SYSTEM_AUDIT_LOG_COLLECTION)
            coll.insert(record_dict)

            logger.info(
                f"AOGA Audit Record saved: {record.record_id}, hash={record_dict['content_hash'][:8]}",
            )
            return record.record_id
        except Exception as e:
            logger.error(f"Failed to record AOGA audit: {e}", exc_info=True)
            raise

    async def update_execution(self, record_id: str, execution_data: Dict[str, Any]):
        """更新執行結果（僅限於追加執行資訊，不改變原始推理資訊）"""
        try:
            coll = self.client.db.collection(SYSTEM_AUDIT_LOG_COLLECTION)
            existing = coll.get(record_id)
            if not existing or not isinstance(existing, dict):
                raise ValueError(f"Audit record {record_id} not found or invalid format")

            # 追加執行數據
            existing["execution"] = execution_data

            # 重新計算雜湊以反映新狀態
            existing["content_hash"] = self._calculate_hash(existing)
            existing["updated_at"] = datetime.utcnow().isoformat()

            coll.update(existing)
            logger.info(f"AOGA Audit Record updated with execution: {record_id}")
        except Exception as e:
            logger.error(f"Failed to update AOGA audit: {e}", exc_info=True)
            raise
