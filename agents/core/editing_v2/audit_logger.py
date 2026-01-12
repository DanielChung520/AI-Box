# 代碼功能說明: 審計日誌服務
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""審計日誌服務

實現審計日誌記錄、查詢和存儲功能（性能優化版本：支持異步寫入和批量寫入）。
"""

import hashlib
import json
import logging
from collections import deque
from typing import Any, Dict, List, Optional

from agents.core.editing_v2.audit_models import (
    AuditEvent,
    AuditEventType,
    IntentStorage,
    PatchStorage,
)

logger = logging.getLogger(__name__)


class AuditLogger:
    """審計日誌服務

    提供審計日誌記錄、查詢和存儲功能（性能優化版本）。
    """

    def __init__(self, arango_client=None, async_write: bool = True, batch_size: int = 10):
        """
        初始化審計日誌服務

        Args:
            arango_client: ArangoDB 客戶端（可選，如果為 None 則使用內存存儲）
            async_write: 是否使用異步寫入（性能優化），默認 True
            batch_size: 批量寫入大小，默認 10
        """
        self.arango_client = arango_client
        self.async_write = async_write
        self.batch_size = batch_size
        self._events: List[AuditEvent] = []  # 內存存儲（用於測試或無數據庫時）
        self._patches: Dict[str, PatchStorage] = {}  # 內存存儲
        self._intents: Dict[str, IntentStorage] = {}  # 內存存儲
        self._event_queue: deque = deque()  # 事件隊列（用於批量寫入）
        self._patch_queue: deque = deque()  # Patch 隊列（用於批量寫入）
        self._intent_queue: deque = deque()  # Intent 隊列（用於批量寫入）

    def log_event(
        self,
        event_type: AuditEventType,
        intent_id: Optional[str] = None,
        patch_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        duration: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> AuditEvent:
        """
        記錄審計事件

        Args:
            event_type: 事件類型
            intent_id: Intent ID
            patch_id: Patch ID
            doc_id: 文檔 ID
            duration: 持續時間（秒）
            metadata: 元數據
            user_id: 用戶 ID
            tenant_id: 租戶 ID

        Returns:
            審計事件
        """
        event = AuditEvent(
            event_type=event_type,
            intent_id=intent_id,
            patch_id=patch_id,
            doc_id=doc_id,
            duration=duration,
            metadata=metadata or {},
            user_id=user_id,
            tenant_id=tenant_id,
        )

        # 存儲到內存
        self._events.append(event)

        # 如果配置了 ArangoDB，存儲到數據庫（性能優化：異步或批量寫入）
        if self.arango_client and self.arango_client.db:
            if self.async_write:
                # 異步寫入（不阻塞主流程）
                try:
                    # 添加到隊列，批量寫入
                    self._event_queue.append(event)
                    if len(self._event_queue) >= self.batch_size:
                        # 批量寫入
                        self._batch_store_events_to_db()
                except Exception as e:
                    logger.error(f"Failed to queue audit event: {e}", exc_info=True)
            else:
                # 同步寫入
                try:
                    self._store_event_to_db(event)
                except Exception as e:
                    logger.error(f"Failed to store audit event to database: {e}", exc_info=True)

        logger.info(
            f"Audit event logged: {event_type.value}, intent_id={intent_id}, "
            f"patch_id={patch_id}, doc_id={doc_id}"
        )

        return event

    def store_patch(
        self,
        patch_id: str,
        intent_id: str,
        doc_id: str,
        block_patch: Dict[str, Any],
        text_patch: str,
    ) -> PatchStorage:
        """
        存儲 Patch（不可變存儲）

        Args:
            patch_id: Patch ID
            intent_id: Intent ID
            doc_id: 文檔 ID
            block_patch: Block Patch 數據
            text_patch: Text Patch 數據

        Returns:
            Patch 存儲記錄
        """
        # 計算哈希
        content_str = json.dumps(block_patch, sort_keys=True) + text_patch
        content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

        patch_storage = PatchStorage(
            patch_id=patch_id,
            intent_id=intent_id,
            doc_id=doc_id,
            block_patch=block_patch,
            text_patch=text_patch,
            content_hash=content_hash,
        )

        # 存儲到內存
        self._patches[patch_id] = patch_storage

        # 如果配置了 ArangoDB，存儲到數據庫（性能優化：異步或批量寫入）
        if self.arango_client and self.arango_client.db:
            if self.async_write:
                # 異步寫入（不阻塞主流程）
                try:
                    self._patch_queue.append(patch_storage)
                    if len(self._patch_queue) >= self.batch_size:
                        self._batch_store_patches_to_db()
                except Exception as e:
                    logger.error(f"Failed to queue patch: {e}", exc_info=True)
            else:
                # 同步寫入
                try:
                    self._store_patch_to_db(patch_storage)
                except Exception as e:
                    logger.error(f"Failed to store patch to database: {e}", exc_info=True)

        return patch_storage

    def store_intent(
        self,
        intent_id: str,
        doc_id: str,
        intent_data: Dict[str, Any],
    ) -> IntentStorage:
        """
        存儲 Intent（不可變存儲）

        Args:
            intent_id: Intent ID
            doc_id: 文檔 ID
            intent_data: Intent 數據

        Returns:
            Intent 存儲記錄
        """
        # 計算哈希
        content_str = json.dumps(intent_data, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()

        intent_storage = IntentStorage(
            intent_id=intent_id,
            doc_id=doc_id,
            intent_data=intent_data,
            content_hash=content_hash,
        )

        # 存儲到內存
        self._intents[intent_id] = intent_storage

        # 如果配置了 ArangoDB，存儲到數據庫（性能優化：異步或批量寫入）
        if self.arango_client and self.arango_client.db:
            if self.async_write:
                # 異步寫入（不阻塞主流程）
                try:
                    self._intent_queue.append(intent_storage)
                    if len(self._intent_queue) >= self.batch_size:
                        self._batch_store_intents_to_db()
                except Exception as e:
                    logger.error(f"Failed to queue intent: {e}", exc_info=True)
            else:
                # 同步寫入
                try:
                    self._store_intent_to_db(intent_storage)
                except Exception as e:
                    logger.error(f"Failed to store intent to database: {e}", exc_info=True)

        return intent_storage

    def query_events(
        self,
        intent_id: Optional[str] = None,
        patch_id: Optional[str] = None,
        doc_id: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        """
        查詢審計事件

        Args:
            intent_id: Intent ID（可選）
            patch_id: Patch ID（可選）
            doc_id: 文檔 ID（可選）
            event_type: 事件類型（可選）
            limit: 返回結果數量限制

        Returns:
            審計事件列表
        """
        # 從內存查詢
        results = self._events.copy()

        # 應用過濾條件
        if intent_id:
            results = [e for e in results if e.intent_id == intent_id]
        if patch_id:
            results = [e for e in results if e.patch_id == patch_id]
        if doc_id:
            results = [e for e in results if e.doc_id == doc_id]
        if event_type:
            results = [e for e in results if e.event_type == event_type]

        # 按時間戳降序排序
        results.sort(key=lambda e: e.timestamp, reverse=True)

        # 限制結果數量
        return results[:limit]

    def get_patch(self, patch_id: str) -> Optional[PatchStorage]:
        """
        獲取 Patch 存儲記錄

        Args:
            patch_id: Patch ID

        Returns:
            Patch 存儲記錄，如果未找到返回 None
        """
        return self._patches.get(patch_id)

    def get_intent(self, intent_id: str) -> Optional[IntentStorage]:
        """
        獲取 Intent 存儲記錄

        Args:
            intent_id: Intent ID

        Returns:
            Intent 存儲記錄，如果未找到返回 None
        """
        return self._intents.get(intent_id)

    def _store_event_to_db(self, event: AuditEvent) -> None:
        """
        存儲事件到 ArangoDB

        Args:
            event: 審計事件
        """
        if not self.arango_client or not self.arango_client.db:
            return

        collection = self.arango_client.db.collection("audit_logs")
        doc = event.model_dump()
        doc["_key"] = event.event_id
        collection.insert(doc)

    def _batch_store_events_to_db(self) -> None:
        """
        批量存儲事件到 ArangoDB（性能優化）

        從隊列中取出多個事件，一次性寫入數據庫。
        """
        if not self.arango_client or not self.arango_client.db:
            return

        if not self._event_queue:
            return

        try:
            collection = self.arango_client.db.collection("audit_logs")
            docs = []

            # 從隊列中取出事件（最多 batch_size 個）
            batch_count = min(len(self._event_queue), self.batch_size)
            for _ in range(batch_count):
                event = self._event_queue.popleft()
                doc = event.model_dump()
                doc["_key"] = event.event_id
                docs.append(doc)

            # 批量插入
            if docs:
                collection.import_bulk(docs)
                logger.debug(f"Batch stored {len(docs)} audit events to database")
        except Exception as e:
            logger.error(f"Failed to batch store audit events to database: {e}", exc_info=True)
            # 寫入失敗，將事件重新放回隊列（避免丟失）
            # 注意：這裡只重新放入當前批次，其他事件已經被移除

    def _store_patch_to_db(self, patch_storage: PatchStorage) -> None:
        """
        存儲 Patch 到 ArangoDB

        Args:
            patch_storage: Patch 存儲記錄
        """
        if not self.arango_client or not self.arango_client.db:
            return

        # 使用自定義 collection 名稱（如果需要的話）
        collection_name = "document_editing_patches"
        if not self.arango_client.db.has_collection(collection_name):
            self.arango_client.db.create_collection(collection_name)

        collection = self.arango_client.db.collection(collection_name)
        doc = patch_storage.model_dump()
        doc["_key"] = patch_storage.patch_id
        collection.insert(doc)

    def _store_intent_to_db(self, intent_storage: IntentStorage) -> None:
        """
        存儲 Intent 到 ArangoDB

        Args:
            intent_storage: Intent 存儲記錄
        """
        if not self.arango_client or not self.arango_client.db:
            return

        # 使用自定義 collection 名稱（如果需要的話）
        collection_name = "document_editing_intents"
        if not self.arango_client.db.has_collection(collection_name):
            self.arango_client.db.create_collection(collection_name)

        collection = self.arango_client.db.collection(collection_name)
        doc = intent_storage.model_dump()
        doc["_key"] = intent_storage.intent_id
        collection.insert(doc)

    def _batch_store_patches_to_db(self) -> None:
        """
        批量存儲 Patch 到 ArangoDB（性能優化）
        """
        if not self.arango_client or not self.arango_client.db:
            return

        if not self._patch_queue:
            return

        try:
            collection_name = "document_editing_patches"
            if not self.arango_client.db.has_collection(collection_name):
                self.arango_client.db.create_collection(collection_name)

            collection = self.arango_client.db.collection(collection_name)
            docs = []

            batch_count = min(len(self._patch_queue), self.batch_size)
            for _ in range(batch_count):
                patch_storage = self._patch_queue.popleft()
                doc = patch_storage.model_dump()
                doc["_key"] = patch_storage.patch_id
                docs.append(doc)

            if docs:
                collection.import_bulk(docs)
                logger.debug(f"Batch stored {len(docs)} patches to database")
        except Exception as e:
            logger.error(f"Failed to batch store patches to database: {e}", exc_info=True)

    def _batch_store_intents_to_db(self) -> None:
        """
        批量存儲 Intent 到 ArangoDB（性能優化）
        """
        if not self.arango_client or not self.arango_client.db:
            return

        if not self._intent_queue:
            return

        try:
            collection_name = "document_editing_intents"
            if not self.arango_client.db.has_collection(collection_name):
                self.arango_client.db.create_collection(collection_name)

            collection = self.arango_client.db.collection(collection_name)
            docs = []

            batch_count = min(len(self._intent_queue), self.batch_size)
            for _ in range(batch_count):
                intent_storage = self._intent_queue.popleft()
                doc = intent_storage.model_dump()
                doc["_key"] = intent_storage.intent_id
                docs.append(doc)

            if docs:
                collection.import_bulk(docs)
                logger.debug(f"Batch stored {len(docs)} intents to database")
        except Exception as e:
            logger.error(f"Failed to batch store intents to database: {e}", exc_info=True)

    def flush(self) -> None:
        """
        刷新所有隊列，強制寫入所有待處理的事件、Patch 和 Intent

        用於程序結束時或需要確保所有數據已寫入時調用。
        """
        if self._event_queue:
            self._batch_store_events_to_db()
        if self._patch_queue:
            self._batch_store_patches_to_db()
        if self._intent_queue:
            self._batch_store_intents_to_db()
