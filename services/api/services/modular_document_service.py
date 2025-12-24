# 代碼功能說明: 模組化文檔服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""模組化文檔服務 - 實現主從架構管理和關聯管理"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.modular_document import (
    ModularDocument,
    ModularDocumentAddSubDocumentRequest,
    ModularDocumentCreate,
    ModularDocumentRemoveSubDocumentRequest,
    ModularDocumentUpdate,
    SubDocumentRef,
)
from services.api.processors.transclusion_parser import (
    build_reference_graph,
    detect_circular_reference,
)

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "modular_documents"


class ModularDocumentService:
    """模組化文檔服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化模組化文檔服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保集合存在"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)
            # 創建索引
            collection = self.client.db.collection(COLLECTION_NAME)
            collection.add_index({"type": "persistent", "fields": ["doc_id"]})
            collection.add_index({"type": "persistent", "fields": ["master_file_id"]})
            collection.add_index({"type": "persistent", "fields": ["task_id"]})
            collection.add_index({"type": "persistent", "fields": ["created_at"]})

    def create(self, create_request: ModularDocumentCreate) -> ModularDocument:
        """
        創建模組化文檔

        Args:
            create_request: 創建請求

        Returns:
            創建的模組化文檔
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        doc_id = create_request.doc_id or str(uuid.uuid4())
        now = datetime.utcnow()

        # 構建子文檔引用列表（轉換為字典格式以便存儲）
        sub_docs = [
            {
                "sub_file_id": sub.sub_file_id,
                "filename": sub.filename,
                "section_title": sub.section_title,
                "order": sub.order,
                "transclusion_syntax": sub.transclusion_syntax,
                "header_path": sub.header_path,
            }
            for sub in create_request.sub_documents
        ]

        doc = {
            "_key": doc_id,
            "doc_id": doc_id,
            "master_file_id": create_request.master_file_id,
            "title": create_request.title,
            "task_id": create_request.task_id,
            "description": create_request.description,
            "metadata": create_request.metadata,
            "sub_documents": sub_docs,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        collection.insert(doc)

        # 構建返回對象
        sub_document_refs = [SubDocumentRef(**sub_doc) for sub_doc in sub_docs]

        return ModularDocument(
            doc_id=doc_id,
            master_file_id=create_request.master_file_id,
            title=create_request.title,
            task_id=create_request.task_id,
            description=create_request.description,
            metadata=create_request.metadata,
            sub_documents=sub_document_refs,
            created_at=now,
            updated_at=now,
        )

    def get(self, doc_id: str) -> Optional[ModularDocument]:
        """
        獲取模組化文檔

        Args:
            doc_id: 模組化文檔 ID

        Returns:
            模組化文檔，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(doc_id)

        if doc is None:
            return None

        if not isinstance(doc, dict):
            return None

        # 轉換子文檔引用
        sub_docs = [SubDocumentRef(**sub_doc) for sub_doc in doc.get("sub_documents", [])]

        return ModularDocument(
            doc_id=doc["doc_id"],
            master_file_id=doc["master_file_id"],
            title=doc["title"],
            task_id=doc["task_id"],
            description=doc.get("description"),
            metadata=doc.get("metadata", {}),
            sub_documents=sub_docs,
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

    def get_by_master_file_id(self, master_file_id: str) -> Optional[ModularDocument]:
        """
        根據主文檔文件 ID 獲取模組化文檔

        Args:
            master_file_id: 主文檔文件 ID

        Returns:
            模組化文檔，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)
        cursor = collection.find({"master_file_id": master_file_id})

        docs = list(cursor)
        if not docs:
            return None

        doc = docs[0]
        if not isinstance(doc, dict):
            return None

        # 轉換子文檔引用
        sub_docs = [SubDocumentRef(**sub_doc) for sub_doc in doc.get("sub_documents", [])]

        return ModularDocument(
            doc_id=doc["doc_id"],
            master_file_id=doc["master_file_id"],
            title=doc["title"],
            task_id=doc["task_id"],
            description=doc.get("description"),
            metadata=doc.get("metadata", {}),
            sub_documents=sub_docs,
            created_at=datetime.fromisoformat(doc["created_at"]),
            updated_at=datetime.fromisoformat(doc["updated_at"]),
        )

    def update(self, doc_id: str, update: ModularDocumentUpdate) -> Optional[ModularDocument]:
        """
        更新模組化文檔

        Args:
            doc_id: 模組化文檔 ID
            update: 更新請求

        Returns:
            更新後的模組化文檔，如果不存在則返回 None
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(doc_id)

        if doc is None:
            return None

        if not isinstance(doc, dict):
            return None

        update_data: Dict[str, Any] = {"updated_at": datetime.utcnow().isoformat()}

        if update.title is not None:
            update_data["title"] = update.title
        if update.description is not None:
            update_data["description"] = update.description
        if update.metadata is not None:
            update_data["metadata"] = update.metadata
        if update.sub_documents is not None:
            update_data["sub_documents"] = [
                {
                    "sub_file_id": sub.sub_file_id,
                    "filename": sub.filename,
                    "section_title": sub.section_title,
                    "order": sub.order,
                    "transclusion_syntax": sub.transclusion_syntax,
                    "header_path": sub.header_path,
                }
                for sub in update.sub_documents
            ]

        collection.update({"_key": doc_id, **update_data})

        # 重新獲取更新後的文檔
        return self.get(doc_id)

    def add_sub_document(
        self, doc_id: str, add_request: ModularDocumentAddSubDocumentRequest
    ) -> Optional[ModularDocument]:
        """
        添加分文檔引用

        Args:
            doc_id: 模組化文檔 ID
            add_request: 添加分文檔請求

        Returns:
            更新後的模組化文檔，如果不存在則返回 None
        """
        modular_doc = self.get(doc_id)
        if modular_doc is None:
            return None

        # 生成 Transclusion 語法
        transclusion_syntax = f"![[{add_request.filename}]]"

        # 確定順序
        existing_orders = [sub.order for sub in modular_doc.sub_documents]
        order = (
            add_request.order
            if add_request.order is not None
            else (max(existing_orders) + 1 if existing_orders else 0)
        )

        # 創建新的分文檔引用
        new_sub_doc = SubDocumentRef(
            sub_file_id=add_request.sub_file_id,
            filename=add_request.filename,
            section_title=add_request.section_title,
            order=order,
            transclusion_syntax=transclusion_syntax,
            header_path=add_request.header_path,
        )

        # 添加到列表並按順序排序
        updated_subs = modular_doc.sub_documents + [new_sub_doc]
        updated_subs.sort(key=lambda x: x.order)

        # 更新文檔
        update = ModularDocumentUpdate(sub_documents=updated_subs)
        return self.update(doc_id, update)

    def remove_sub_document(
        self, doc_id: str, remove_request: ModularDocumentRemoveSubDocumentRequest
    ) -> Optional[ModularDocument]:
        """
        移除分文檔引用

        Args:
            doc_id: 模組化文檔 ID
            remove_request: 移除分文檔請求

        Returns:
            更新後的模組化文檔，如果不存在則返回 None
        """
        modular_doc = self.get(doc_id)
        if modular_doc is None:
            return None

        # 過濾掉要移除的分文檔
        updated_subs = [
            sub
            for sub in modular_doc.sub_documents
            if sub.sub_file_id != remove_request.sub_file_id
        ]

        # 更新文檔
        update = ModularDocumentUpdate(sub_documents=updated_subs)
        return self.update(doc_id, update)

    def validate_references(self, doc_id: str, existing_file_ids: Set[str]) -> bool:
        """
        驗證模組化文檔的所有引用是否有效

        Args:
            doc_id: 模組化文檔 ID
            existing_file_ids: 現有文件 ID 集合

        Returns:
            如果所有引用都有效則返回 True，否則返回 False
        """
        modular_doc = self.get(doc_id)
        if modular_doc is None:
            return False

        # 檢查所有子文檔引用
        for sub_doc in modular_doc.sub_documents:
            if sub_doc.sub_file_id not in existing_file_ids:
                self.logger.warning(
                    f"Sub-document reference invalid: {sub_doc.sub_file_id}",
                    doc_id=doc_id,
                    sub_file_id=sub_doc.sub_file_id,
                )
                return False

        return True

    def check_circular_reference(self, doc_id: str) -> Optional[List[str]]:
        """
        檢查模組化文檔是否存在循環引用

        Args:
            doc_id: 模組化文檔 ID

        Returns:
            如果檢測到循環，返回循環路徑；否則返回 None
        """
        modular_doc = self.get(doc_id)
        if modular_doc is None:
            return None

        # 構建引用圖（僅考慮當前文檔的直接引用）
        # 注意：完整的循環檢測需要遍歷所有相關文檔
        doc_references: Dict[str, List[str]] = {
            doc_id: [sub.sub_file_id for sub in modular_doc.sub_documents]
        }

        # 如果子文檔也是模組化文檔，需要遞歸檢查
        # 這裡簡化處理，只檢查直接引用
        reference_graph = build_reference_graph(doc_references)

        # 檢測循環（僅在直接引用中）
        cycle = detect_circular_reference(doc_id, reference_graph)
        return cycle

    def list_by_task_id(self, task_id: str) -> List[ModularDocument]:
        """
        根據任務 ID 列出所有模組化文檔

        Args:
            task_id: 任務 ID

        Returns:
            模組化文檔列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)
        cursor = collection.find({"task_id": task_id})

        results: List[ModularDocument] = []
        for doc in cursor:
            if not isinstance(doc, dict):
                continue

            sub_docs = [SubDocumentRef(**sub_doc) for sub_doc in doc.get("sub_documents", [])]

            results.append(
                ModularDocument(
                    doc_id=doc["doc_id"],
                    master_file_id=doc["master_file_id"],
                    title=doc["title"],
                    task_id=doc["task_id"],
                    description=doc.get("description"),
                    metadata=doc.get("metadata", {}),
                    sub_documents=sub_docs,
                    created_at=datetime.fromisoformat(doc["created_at"]),
                    updated_at=datetime.fromisoformat(doc["updated_at"]),
                )
            )

        return results

    def delete(self, doc_id: str) -> bool:
        """
        刪除模組化文檔

        Args:
            doc_id: 模組化文檔 ID

        Returns:
            如果刪除成功則返回 True，否則返回 False
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = self.client.db.collection(COLLECTION_NAME)
        try:
            collection.delete(doc_id)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete modular document: {e}", doc_id=doc_id)
            return False
