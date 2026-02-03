# 代碼功能說明: 文件元數據服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-28

"""文件元數據服務 - 實現 ArangoDB CRUD 和全文搜索"""

from datetime import datetime
from typing import List, Optional

import structlog

from database.arangodb import ArangoDBClient
from services.api.models.data_classification import DataClassification
from services.api.models.file_access_control import FileAccessControl, FileAccessLevel
from services.api.models.file_metadata import FileMetadata, FileMetadataCreate, FileMetadataUpdate

logger = structlog.get_logger(__name__)

COLLECTION_NAME = "file_metadata"


class FileMetadataService:
    """文件元數據服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化元數據服務

        Args:
            client: ArangoDB 客戶端（可選，如果不提供則自動創建）
        """
        self.client = client or ArangoDBClient()
        self.logger = logger
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """確保集合存在並創建所有必要的索引（包括 KA 屬性索引）"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        if not self.client.db.has_collection(COLLECTION_NAME):
            self.client.db.create_collection(COLLECTION_NAME)

        # 獲取現有索引名稱列表
        existing_indexes = collection.indexes()
        index_names = {idx.get("name", "") for idx in existing_indexes}

        # 基礎索引
        base_indexes = [
            {"name": "idx_file_id", "fields": ["file_id"]},
            {"name": "idx_filename", "fields": ["filename"]},
            {"name": "idx_file_type", "fields": ["file_type"]},
            {"name": "idx_upload_time", "fields": ["upload_time"]},
            {"name": "idx_user_id", "fields": ["user_id"]},
            {"name": "idx_task_id", "fields": ["task_id"]},
            {"name": "idx_folder_id", "fields": ["folder_id"]},
            {"name": "idx_status", "fields": ["status"]},
        ]

        # 訪問控制相關索引
        access_control_indexes = [
            {"name": "idx_access_level", "fields": ["access_control.access_level"]},
            {"name": "idx_owner_id", "fields": ["access_control.owner_id"]},
            {"name": "idx_data_classification", "fields": ["data_classification"]},
        ]

        # 知識資產（KA）相關索引（v4.4 新增）
        ka_indexes = [
            {"name": "idx_knw_code", "fields": ["knw_code"]},
            {"name": "idx_ka_id", "fields": ["ka_id"]},
            {"name": "idx_domain", "fields": ["domain"]},
            {"name": "idx_major", "fields": ["major"]},
            {"name": "idx_lifecycle_state", "fields": ["lifecycle_state"]},
            {"name": "idx_version", "fields": ["version"]},
            {"name": "idx_task_user", "fields": ["task_id", "user_id"]},  # 複合索引
        ]

        # 創建所有索引（如果不存在）
        all_indexes = base_indexes + access_control_indexes + ka_indexes
        for idx_config in all_indexes:
            if idx_config["name"] not in index_names:
                collection.add_index(
                    {
                        "type": "persistent",
                        "fields": idx_config["fields"],
                        "name": idx_config["name"],
                    }
                )

        # 複合索引（用於權限查詢優化）
        composite_idx_name = "idx_access_composite"
        if composite_idx_name not in index_names:
            collection.add_index(
                {
                    "type": "persistent",
                    "fields": [
                        "access_control.access_level",
                        "access_control.owner_id",
                        "data_classification",
                    ],
                    "name": composite_idx_name,
                }
            )

    @staticmethod
    def get_default_access_control(
        user_id: str,
        tenant_id: Optional[str] = None,
        is_system_file: bool = False,
    ) -> FileAccessControl:
        """獲取默認的文件訪問控制配置

        AI治理原則：默認私有，最小權限
        系統文件：自動設置 SystemSecurity 安全組授權

        Args:
            user_id: 文件所有者用戶ID
            tenant_id: 文件所有者租戶ID（可選）
            is_system_file: 是否為系統文件（默認 False）

        Returns:
            默認的 FileAccessControl 配置
        """
        if is_system_file:
            # 系統文件：使用 SECURITY_GROUP 級別，授權 SystemSecurity 安全組
            return FileAccessControl(
                access_level=FileAccessLevel.SECURITY_GROUP.value,
                owner_id=user_id,
                owner_tenant_id=tenant_id,
                data_classification=DataClassification.INTERNAL.value,
                sensitivity_labels=[],
                authorized_security_groups=["SystemSecurity"],  # 系統安全組
            )
        else:
            # 普通文件：默認私有
            return FileAccessControl(
                access_level=FileAccessLevel.PRIVATE.value,  # 默認私有
                owner_id=user_id,
                owner_tenant_id=tenant_id,
                data_classification=DataClassification.INTERNAL.value,  # 默認內部
                sensitivity_labels=[],
                authorized_users=[user_id],  # 默認只有所有者
            )

    def create(self, metadata: FileMetadataCreate) -> FileMetadata:
        """創建文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 如果未提供 access_control，自動生成默認配置（向後兼容）
        access_control = metadata.access_control
        if access_control is None:
            # 判斷是否為系統文件（路徑包含 "docs/系统设计文档" 或 "docs/系統設計文檔"）
            is_system_file = False
            if metadata.storage_path:
                storage_path_lower = metadata.storage_path.lower()
                is_system_file = (
                    "docs/系统设计文档" in storage_path_lower
                    or "docs/系統設計文檔" in storage_path_lower
                    or "system_design" in storage_path_lower
                )

            access_control = self.get_default_access_control(
                user_id=metadata.user_id or "unknown",
                tenant_id=None,  # 可以從上下文獲取，暫時設為 None
                is_system_file=is_system_file,
            )

        # 同步 data_classification 和 sensitivity_labels
        data_classification = metadata.data_classification or access_control.data_classification
        sensitivity_labels = metadata.sensitivity_labels or access_control.sensitivity_labels

        doc = {
            "_key": metadata.file_id,
            "file_id": metadata.file_id,
            "filename": metadata.filename,
            "file_type": metadata.file_type,
            "file_size": metadata.file_size,
            "user_id": metadata.user_id,
            "task_id": metadata.task_id,
            "folder_id": metadata.folder_id,
            "storage_path": metadata.storage_path,
            "tags": metadata.tags,
            "description": metadata.description,
            "custom_metadata": metadata.custom_metadata,
            "status": metadata.status or "uploaded",
            "processing_status": metadata.processing_status,
            "chunk_count": metadata.chunk_count,
            "vector_count": metadata.vector_count,
            "kg_status": metadata.kg_status,
            "access_control": access_control.model_dump(),
            "data_classification": data_classification,
            "sensitivity_labels": sensitivity_labels,
            "upload_time": datetime.utcnow().isoformat(),
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        collection = self.client.db.collection(COLLECTION_NAME)
        # 修改時間：2026-01-05 - 檢查文件是否已存在，避免重複創建
        try:
            existing = collection.get(metadata.file_id)
            if existing:
                # 文件已存在，記錄警告並返回現有記錄
                self.logger.warning(
                    "File metadata already exists, skipping creation",
                    file_id=metadata.file_id,
                    filename=metadata.filename,
                )
                # 返回現有的文件元數據
                return FileMetadata(
                    file_id=existing.get("file_id") or existing.get("_key", ""),  # type: ignore[arg-type]
                    filename=existing.get("filename", ""),  # type: ignore[arg-type]
                    file_type=existing.get("file_type", ""),  # type: ignore[arg-type]
                    file_size=existing.get("file_size", 0),  # type: ignore[arg-type]
                    user_id=existing.get("user_id"),  # type: ignore[arg-type]
                    task_id=existing.get("task_id", ""),  # type: ignore[arg-type]
                    folder_id=existing.get("folder_id"),  # type: ignore[arg-type]
                    storage_path=existing.get("storage_path"),  # type: ignore[arg-type]
                    tags=existing.get("tags", []),  # type: ignore[arg-type]
                    description=existing.get("description"),  # type: ignore[arg-type]
                    custom_metadata=existing.get("custom_metadata", {}),  # type: ignore[arg-type]
                    status=existing.get("status", "uploaded"),  # type: ignore[arg-type]
                    processing_status=existing.get("processing_status"),  # type: ignore[arg-type]
                    chunk_count=existing.get("chunk_count"),  # type: ignore[arg-type]
                    vector_count=existing.get("vector_count"),  # type: ignore[arg-type]
                    kg_status=existing.get("kg_status"),  # type: ignore[arg-type]
                    access_control=(
                        FileAccessControl(**existing["access_control"])
                        if existing.get("access_control")
                        else None
                    ),  # type: ignore[arg-type]
                    data_classification=existing.get("data_classification"),  # type: ignore[arg-type]
                    sensitivity_labels=existing.get("sensitivity_labels", []),  # type: ignore[arg-type]
                    upload_time=datetime.fromisoformat(
                        existing.get("upload_time", datetime.utcnow().isoformat())
                    ),  # type: ignore[arg-type]
                    created_at=(
                        datetime.fromisoformat(existing["created_at"])
                        if existing.get("created_at")
                        else None
                    ),  # type: ignore[arg-type]
                    updated_at=(
                        datetime.fromisoformat(existing["updated_at"])
                        if existing.get("updated_at")
                        else None
                    ),  # type: ignore[arg-type]
                )
        except Exception as e:
            # 文件不存在，繼續創建
            self.logger.debug(
                "File does not exist, will create new", file_id=metadata.file_id, error=str(e)
            )

        self.logger.info(
            "Inserting metadata document", file_id=metadata.file_id, collection=COLLECTION_NAME
        )
        try:
            result = collection.insert(doc)
            self.logger.info(
                "Metadata document inserted successfully", file_id=metadata.file_id, result=result
            )
        except Exception as e:
            self.logger.error(
                "Failed to insert metadata document",
                file_id=metadata.file_id,
                error=str(e),
                exc_info=True,
            )
            raise

        # 確保所有必需字段都存在且類型正確
        return FileMetadata(
            file_id=doc.get("file_id") or doc.get("_key", ""),  # type: ignore[arg-type]  # 已確保存在
            filename=doc.get("filename", ""),  # type: ignore[arg-type]  # 已確保存在
            file_type=doc.get("file_type", ""),  # type: ignore[arg-type]  # 已確保存在
            file_size=doc.get("file_size", 0),  # type: ignore[arg-type]  # 已確保存在
            user_id=doc.get("user_id"),  # type: ignore[arg-type]  # Optional
            task_id=doc.get("task_id", ""),  # type: ignore[arg-type]  # 已確保存在
            folder_id=doc.get("folder_id"),  # type: ignore[arg-type]  # Optional
            storage_path=doc.get("storage_path"),  # type: ignore[arg-type]  # Optional
            tags=doc.get("tags", []),  # type: ignore[arg-type]  # 有默認值
            description=doc.get("description"),  # type: ignore[arg-type]  # Optional
            custom_metadata=doc.get("custom_metadata", {}),  # type: ignore[arg-type]  # 有默認值
            status=doc.get("status", "uploaded"),  # type: ignore[arg-type]  # 有默認值
            processing_status=doc.get("processing_status"),  # type: ignore[arg-type]  # Optional
            chunk_count=doc.get("chunk_count"),  # type: ignore[arg-type]  # Optional
            vector_count=doc.get("vector_count"),  # type: ignore[arg-type]  # Optional
            kg_status=doc.get("kg_status"),  # type: ignore[arg-type]  # Optional
            access_control=(
                FileAccessControl(**doc["access_control"]) if doc.get("access_control") else None
            ),  # type: ignore[arg-type]  # Optional
            data_classification=doc.get("data_classification"),  # type: ignore[arg-type]  # Optional
            sensitivity_labels=doc.get("sensitivity_labels", []),  # type: ignore[arg-type]  # 有默認值
            upload_time=datetime.fromisoformat(
                doc.get("upload_time", datetime.utcnow().isoformat())
            ),  # type: ignore[arg-type]  # 已確保存在
            created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,  # type: ignore[arg-type]  # Optional
            updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,  # type: ignore[arg-type]  # Optional
        )

    def get(self, file_id: str) -> Optional[FileMetadata]:
        """獲取文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None

        if doc is None:
            return None

        # 確保 doc 是字典類型
        if not isinstance(doc, dict):
            return None

        return FileMetadata(**doc)

    def update(self, file_id: str, update: FileMetadataUpdate) -> Optional[FileMetadata]:
        """更新文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        doc = collection.get(file_id)

        if doc is None:
            return None

        update_data: dict = {"updated_at": datetime.utcnow().isoformat()}

        # 修改時間：2025-12-08 10:21:00 UTC+8 - 支持將 task_id 更新為 None
        # Pydantic 模型中，即使 task_id=None，model.task_id 也存在
        # 所以需要檢查是否在 model_dump 中包含 'task_id' 鍵
        update_dict = update.model_dump(exclude_unset=True)
        if "task_id" in update_dict:
            # 即使是 None 也要更新（表示移動到任務工作區）
            update_data["task_id"] = update.task_id
        if "folder_id" in update_dict:
            update_data["folder_id"] = update.folder_id
        if update.tags is not None:
            update_data["tags"] = update.tags
        if update.description is not None:
            update_data["description"] = update.description
        if update.custom_metadata is not None:
            update_data["custom_metadata"] = update.custom_metadata
        if update.status is not None:
            update_data["status"] = update.status
        if update.processing_status is not None:
            update_data["processing_status"] = update.processing_status
        if update.chunk_count is not None:
            update_data["chunk_count"] = update.chunk_count
        if update.vector_count is not None:
            update_data["vector_count"] = update.vector_count
        if update.kg_status is not None:
            update_data["kg_status"] = update.kg_status

        # 更新訪問控制配置
        if update.access_control is not None:
            update_data["access_control"] = update.access_control.model_dump()
            # 同步更新 data_classification 和 sensitivity_labels
            if update.access_control.data_classification:
                update_data["data_classification"] = update.access_control.data_classification
            if update.access_control.sensitivity_labels:
                update_data["sensitivity_labels"] = update.access_control.sensitivity_labels

        # 知識資產（KA）核心屬性（v4.4 新增）
        if update.knw_code is not None:
            update_data["knw_code"] = update.knw_code
        if update.ka_id is not None:
            update_data["ka_id"] = update.ka_id
        if update.domain is not None:
            update_data["domain"] = update.domain
        if update.major is not None:
            update_data["major"] = update.major
        if update.lifecycle_state is not None:
            update_data["lifecycle_state"] = update.lifecycle_state
        if update.version is not None:
            update_data["version"] = update.version
        if update.license is not None:
            update_data["license"] = update.license
        if update.validity_scope is not None:
            update_data["validity_scope"] = update.validity_scope
        if update.vector_refs is not None:
            update_data["vector_refs"] = update.vector_refs
        if update.graph_refs is not None:
            update_data["graph_refs"] = update.graph_refs
        if update.supersedes is not None:
            update_data["supersedes"] = update.supersedes
        if update.superseded_by is not None:
            update_data["superseded_by"] = update.superseded_by
        if update.version_history is not None:
            update_data["version_history"] = update.version_history

        # ArangoDB collection.update() 需要 {'_key': ...} 或 {'_id': ...} 作為第一個參數
        # 將 file_id 作為 _key 傳遞
        doc_to_update = {"_key": file_id}
        doc_to_update.update(update_data)

        collection.update(doc_to_update)  # type: ignore[arg-type]  # update 接受 dict
        updated_doc = collection.get(file_id)  # type: ignore[assignment]  # 同步模式下返回 dict | None

        if updated_doc is None or not isinstance(updated_doc, dict):
            return None
        return FileMetadata(**updated_doc)

    def delete(self, file_id: str) -> bool:
        """刪除文件元數據"""
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        collection = self.client.db.collection(COLLECTION_NAME)
        try:
            collection.delete(file_id)
            return True
        except Exception:
            return False

    def list(
        self,
        file_type: Optional[str] = None,
        user_id: Optional[str] = None,
        task_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        domain: Optional[str] = None,
        major: Optional[str] = None,
        lifecycle_state: Optional[str] = None,
        knw_code_not_null: bool = False,
        limit: int = 100,
        offset: int = 0,
        sort_by: str = "upload_time",
        sort_order: str = "desc",
        caller_is_ka_agent: bool = False,
    ) -> List[FileMetadata]:
        """查詢文件元數據列表。

        支援 KA 檢索過濾（v4.4）：domain、major、lifecycle_state、knw_code_not_null。

        當 caller_is_ka_agent=True 時，不套用 user_id / task_id 過濾：
        KA-Agent 為知識管理員，對所有已上架知識文件有權限，不因「哪個人物/任務」而限縮。
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")

        # 構建 AQL 查詢
        filter_conditions = []
        bind_vars: dict = {}

        if file_type:
            filter_conditions.append("doc.file_type == @file_type")
            bind_vars["file_type"] = file_type

        # KA-Agent 為知識管理員：不依 user_id / task_id 過濾，對所有知識文件有權限
        if not caller_is_ka_agent:
            if user_id:
                filter_conditions.append("doc.user_id == @user_id")
                bind_vars["user_id"] = user_id

            if task_id is not None:
                filter_conditions.append("doc.task_id == @task_id")
                bind_vars["task_id"] = task_id

        if tags:
            filter_conditions.append("LENGTH(INTERSECTION(doc.tags, @tags)) > 0")
            bind_vars["tags"] = tags

        if domain:
            filter_conditions.append("doc.domain == @domain")
            bind_vars["domain"] = domain

        if major:
            filter_conditions.append("doc.major == @major")
            bind_vars["major"] = major

        if lifecycle_state:
            filter_conditions.append("doc.lifecycle_state == @lifecycle_state")
            bind_vars["lifecycle_state"] = lifecycle_state

        if knw_code_not_null:
            filter_conditions.append("doc.knw_code != null")

        # 構建完整的 AQL 語句
        aql = f"FOR doc IN {COLLECTION_NAME}"
        if filter_conditions:
            aql += " FILTER " + " AND ".join(filter_conditions)
        else:
            aql += " FILTER 1 == 1"

        aql += f" SORT doc.{sort_by} {sort_order.upper()}"
        # ArangoDB LIMIT 語法：LIMIT offset, count 或 LIMIT count
        # 如果 offset 為 0，可以只使用 LIMIT count
        if offset > 0:
            aql += " LIMIT @offset, @limit"
            bind_vars["offset"] = offset
            bind_vars["limit"] = limit
        else:
            aql += " LIMIT @limit"
            bind_vars["limit"] = limit

        # 添加 RETURN 語句（AQL 查詢必須有 RETURN）
        aql += " RETURN doc"

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results

    def search(
        self,
        query: str,
        user_id: Optional[str] = None,
        file_type: Optional[str] = None,
        task_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[FileMetadata]:
        """全文搜索

        修改時間：2025-01-27 - 添加 task_id 參數，支持在指定任務工作區中搜索
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")
        if self.client.db.aql is None:
            raise RuntimeError("ArangoDB AQL is not available")
        aql = f"""
        FOR doc IN {COLLECTION_NAME}
        FILTER (doc.filename LIKE @query
           OR doc.description LIKE @query
           OR @query IN doc.tags)
        """
        bind_vars: dict = {
            "query": f"%{query}%",
            "limit": limit,
        }

        if user_id:
            aql += " AND doc.user_id == @user_id"
            bind_vars["user_id"] = user_id

        if file_type:
            aql += " AND doc.file_type == @file_type"
            bind_vars["file_type"] = file_type

        # 修改時間：2025-01-27 - 如果提供了 task_id，只搜索該任務工作區的文件
        if task_id:
            aql += " AND doc.task_id == @task_id"
            bind_vars["task_id"] = task_id

        aql += " LIMIT @limit"

        cursor = self.client.db.aql.execute(aql, bind_vars=bind_vars)
        results = [FileMetadata(**doc) for doc in cursor]

        return results


# 單例服務實例
_metadata_service: Optional[FileMetadataService] = None


def get_metadata_service() -> FileMetadataService:
    """獲取文件元數據服務單例"""
    global _metadata_service
    if _metadata_service is None:
        _metadata_service = FileMetadataService()
    return _metadata_service
