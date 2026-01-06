# 代碼功能說明: Ontology 存儲服務 - 提供 Ontology 的 CRUD 操作和多租戶支援
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-01

"""Ontology Store Service

提供 Ontology 的 CRUD 操作，支援多租戶隔離和版本控制。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.ontology import OntologyCreate, OntologyModel, OntologyUpdate
from services.api.models.version_history import VersionHistoryCreate

logger = structlog.get_logger(__name__)

ONTOLOGIES_COLLECTION = "ontologies"


def _generate_ontology_key(
    type: str, name: str, version: str, tenant_id: Optional[str] = None
) -> str:
    """生成 Ontology 的 _key"""
    base_key = f"{type}-{name}-{version}"
    if tenant_id:
        return f"{base_key}-{tenant_id}"
    return base_key


def _document_to_model(doc: Dict[str, Any]) -> OntologyModel:
    """將 ArangoDB document 轉換為 OntologyModel"""
    type_val = doc.get("type")
    name_val = doc.get("name")
    version_val = doc.get("version")
    ontology_name_val = doc.get("ontology_name")
    if not type_val or not isinstance(type_val, str):
        raise ValueError(f"Invalid type: {type_val}")
    if not name_val or not isinstance(name_val, str):
        raise ValueError(f"Invalid name: {name_val}")
    if not version_val or not isinstance(version_val, str):
        raise ValueError(f"Invalid version: {version_val}")
    if not ontology_name_val or not isinstance(ontology_name_val, str):
        raise ValueError(f"Invalid ontology_name: {ontology_name_val}")
    return OntologyModel(
        id=doc.get("_key"),
        tenant_id=doc.get("tenant_id"),
        type=type_val,  # type: ignore[arg-type]  # 已檢查為 str
        name=name_val,  # type: ignore[arg-type]  # 已檢查為 str
        version=version_val,  # type: ignore[arg-type]  # 已檢查為 str
        default_version=doc.get("default_version", False),
        ontology_name=ontology_name_val,  # type: ignore[arg-type]  # 已檢查為 str
        description=doc.get("description"),
        author=doc.get("author"),
        last_modified=doc.get("last_modified"),
        inherits_from=doc.get("inherits_from", []),
        compatible_domains=doc.get("compatible_domains", []),
        tags=doc.get("tags", []),
        use_cases=doc.get("use_cases", []),
        entity_classes=doc.get("entity_classes", []),
        object_properties=doc.get("object_properties", []),
        metadata=doc.get("metadata", {}),
        is_active=doc.get("is_active", True),
        # WBS-4.2.1: 數據分類與標記
        data_classification=doc.get("data_classification"),
        sensitivity_labels=doc.get("sensitivity_labels"),
        created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
        updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        created_by=doc.get("created_by"),
        updated_by=doc.get("updated_by"),
    )


def _model_to_document(model: OntologyModel, include_id: bool = True) -> Dict[str, Any]:
    """將 OntologyModel 轉換為 ArangoDB document"""
    doc: Dict[str, Any] = {
        "tenant_id": model.tenant_id,
        "type": model.type,
        "name": model.name,
        "version": model.version,
        "default_version": model.default_version,
        "ontology_name": model.ontology_name,
        "description": model.description,
        "author": model.author,
        "last_modified": model.last_modified,
        "inherits_from": model.inherits_from,
        "compatible_domains": model.compatible_domains,
        "tags": model.tags,
        "use_cases": model.use_cases,
        "entity_classes": [ec.model_dump() for ec in model.entity_classes],
        "object_properties": [op.model_dump() for op in model.object_properties],
        "metadata": model.metadata,
        "is_active": model.is_active,
        # WBS-4.2.1: 數據分類與標記
        "data_classification": model.data_classification,
        "sensitivity_labels": model.sensitivity_labels,
    }

    if include_id and model.id:
        doc["_key"] = model.id

    if model.created_at:
        doc["created_at"] = model.created_at.isoformat()
    if model.updated_at:
        doc["updated_at"] = model.updated_at.isoformat()

    doc["created_by"] = model.created_by
    doc["updated_by"] = model.updated_by

    return doc


class OntologyStoreService:
    """Ontology 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Ontology Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collection 存在
        collection = self._client.get_or_create_collection(ONTOLOGIES_COLLECTION)
        self._collection = ArangoCollection(collection)

        # 延遲初始化版本歷史服務（可選）
        self._version_history_service: Optional[Any] = None

    def save_ontology(
        self,
        ontology: OntologyCreate,
        tenant_id: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> str:
        """
        保存 Ontology（創建或更新）

        Args:
            ontology: Ontology 創建數據
            tenant_id: 租戶 ID，如果為 None 則使用 ontology.tenant_id
            changed_by: 變更者（用戶 ID），用於版本歷史記錄（可選）

        Returns:
            Ontology ID
        """
        final_tenant_id = tenant_id or ontology.tenant_id
        ontology_key = _generate_ontology_key(
            ontology.type, ontology.name, ontology.version, final_tenant_id
        )

        now = datetime.utcnow().isoformat()

        # 獲取舊版本數據（用於版本歷史記錄）
        existing = self._collection.get(ontology_key)
        previous_version_data: Dict[str, Any] = {}
        if existing:
            # 複製現有數據作為舊版本
            previous_version_data = dict(existing)

        doc: Dict[str, Any] = {
            "_key": ontology_key,
            "tenant_id": final_tenant_id,
            "type": ontology.type,
            "name": ontology.name,
            "version": ontology.version,
            "default_version": ontology.default_version,
            "ontology_name": ontology.ontology_name,
            "description": ontology.description,
            "author": ontology.author,
            "last_modified": ontology.last_modified or now,
            "inherits_from": ontology.inherits_from,
            "compatible_domains": ontology.compatible_domains,
            "tags": ontology.tags,
            "use_cases": ontology.use_cases,
            "entity_classes": ontology.entity_classes,
            "object_properties": ontology.object_properties,
            "metadata": ontology.metadata,
            "is_active": True,
            # WBS-4.2.1: 數據分類與標記
            "data_classification": ontology.data_classification,
            "sensitivity_labels": ontology.sensitivity_labels,
            "created_at": now,
            "updated_at": now,
        }

        try:
            if existing:
                # 更新
                doc["created_at"] = existing.get("created_at", now)
                doc["_key"] = existing.get("_key", ontology_key)
                self._collection.update(doc)
                self._logger.info("ontology_updated", id=ontology_key, tenant_id=final_tenant_id)
                change_type = "update"
            else:
                # 創建
                self._collection.insert(doc)
                self._logger.info("ontology_created", id=ontology_key, tenant_id=final_tenant_id)
                change_type = "create"

            # 記錄版本歷史（可選，失敗不影響主流程）
            if changed_by:
                self._record_version_history(
                    resource_type="ontologies",
                    resource_id=ontology_key,
                    change_type=change_type,
                    changed_by=changed_by,
                    previous_version=previous_version_data,
                    current_version=doc,
                )

            return ontology_key
        except Exception as exc:
            self._logger.error("ontology_save_failed", id=ontology_key, error=str(exc))
            raise

    def _record_version_history(
        self,
        resource_type: str,
        resource_id: str,
        change_type: str,
        changed_by: str,
        previous_version: Dict[str, Any],
        current_version: Dict[str, Any],
    ) -> None:
        """記錄版本歷史（後台執行，失敗不影響主流程）"""
        try:
            # 延遲導入，避免循環依賴
            from services.api.services.governance.version_history_service import (
                SeaweedFSVersionHistoryService,
            )

            # 延遲初始化版本歷史服務
            if self._version_history_service is None:
                try:
                    self._version_history_service = SeaweedFSVersionHistoryService()
                except Exception as e:
                    self._logger.warning(
                        "Failed to initialize version history service",
                        error=str(e),
                    )
                    return

            # 創建版本歷史記錄
            version_data = VersionHistoryCreate(
                resource_type=resource_type,
                resource_id=resource_id,
                change_type=change_type,
                changed_by=changed_by,
                change_summary=f"{change_type.title()} ontology: {current_version.get('ontology_name', resource_id)}",
                previous_version=previous_version,
                current_version=current_version,
            )

            # 嘗試在異步上下文中執行（如果可用）
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果事件循環正在運行，使用 create_task（不阻塞）
                    asyncio.create_task(self._version_history_service.create_version(version_data))
                else:
                    # 如果沒有運行的事件循環，使用 run
                    asyncio.run(self._version_history_service.create_version(version_data))
            except RuntimeError:
                # 沒有事件循環，創建新的
                try:
                    asyncio.run(self._version_history_service.create_version(version_data))
                except Exception as run_error:
                    self._logger.warning(
                        "Failed to run version history recording",
                        error=str(run_error),
                    )
        except Exception as e:
            # 版本歷史記錄失敗不影響主流程
            self._logger.warning(
                "Failed to record version history",
                resource_type=resource_type,
                resource_id=resource_id,
                error=str(e),
            )

    def get_ontology(
        self, ontology_id: str, tenant_id: Optional[str] = None
    ) -> Optional[OntologyModel]:
        """
        獲取 Ontology

        Args:
            ontology_id: Ontology ID
            tenant_id: 租戶 ID（用於驗證）

        Returns:
            OntologyModel 或 None
        """
        try:
            doc = self._collection.get(ontology_id)
            if not doc:
                return None

            # 驗證租戶隔離
            if tenant_id is not None and doc.get("tenant_id") not in [tenant_id, None]:
                self._logger.warning(
                    "ontology_access_denied",
                    id=ontology_id,
                    requested_tenant=tenant_id,
                    actual_tenant=doc.get("tenant_id"),
                )
                return None

            return _document_to_model(doc)
        except Exception as exc:
            self._logger.error("ontology_get_failed", id=ontology_id, error=str(exc))
            raise

    def get_ontology_with_priority(
        self, name: str, type: str, tenant_id: Optional[str] = None, version: Optional[str] = None
    ) -> Optional[OntologyModel]:
        """
        根據優先級查詢 Ontology（租戶專屬 > 全局共享）

        Args:
            name: Ontology 名稱
            type: Ontology 類型
            tenant_id: 租戶 ID
            version: 版本號，如果為 None 則查詢默認版本

        Returns:
            OntologyModel 或 None
        """
        try:
            # 如果指定了版本，直接查詢
            if version:
                if tenant_id:
                    tenant_key = _generate_ontology_key(type, name, version, tenant_id)
                    tenant_ontology = self.get_ontology(tenant_key, tenant_id)
                    if tenant_ontology:
                        return tenant_ontology

                global_key = _generate_ontology_key(type, name, version, None)
                return self.get_ontology(global_key, None)

            # 查詢默認版本（優先租戶專屬）
            if tenant_id:
                # 先查詢租戶專屬的默認版本
                filters: Dict[str, Any] = {
                    "tenant_id": tenant_id,
                    "type": type,
                    "name": name,
                    "default_version": True,
                    "is_active": True,
                }
                results = self._collection.find(filters, limit=1, sort=["-created_at"])
                if results:
                    return _document_to_model(results[0])

            # 再查詢全局共享的默認版本
            filters = {
                "tenant_id": None,
                "type": type,
                "name": name,
                "default_version": True,
                "is_active": True,
            }
            results = self._collection.find(filters, limit=1, sort=["-created_at"])
            if results:
                return _document_to_model(results[0])

            return None
        except Exception as exc:
            self._logger.error(
                "ontology_get_priority_failed",
                name=name,
                type=type,
                tenant_id=tenant_id,
                error=str(exc),
            )
            raise

    def list_ontologies(
        self,
        tenant_id: Optional[str] = None,
        type: Optional[str] = None,
        name: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_active: Optional[bool] = True,
        skip: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[OntologyModel]:
        """
        列表查詢 Ontology

        Args:
            tenant_id: 租戶 ID（如果提供，則查詢租戶專屬和全局共享）
            type: 過濾類型
            name: 名稱模糊搜索（未實現，需要 AQL）
            tags: 標籤過濾（未實現，需要 AQL）
            is_active: 是否啟用
            skip: 跳過數量
            limit: 返回數量限制

        Returns:
            OntologyModel 列表
        """
        try:
            filters: Dict[str, Any] = {}
            if is_active is not None:
                filters["is_active"] = is_active
            if type:
                filters["type"] = type
            if name:
                # 簡單的前綴匹配（完整實現需要使用 AQL）
                filters["name"] = name

            # 租戶過濾：查詢租戶專屬或全局共享
            if tenant_id is not None:
                # 使用 AQL 查詢以支援 OR 條件
                aql = """
                FOR doc IN ontologies
                    FILTER doc.tenant_id == @tenant_id OR doc.tenant_id == null
                    FILTER doc.is_active == @is_active
                """
                bind_vars: Dict[str, Any] = {
                    "tenant_id": tenant_id,
                    "is_active": is_active if is_active is not None else True,
                }
                if type:
                    aql += " FILTER doc.type == @type"
                    bind_vars["type"] = type

                # AQL LIMIT syntax: LIMIT offset, count
                aql += " LIMIT @skip, @limit RETURN doc"
                bind_vars["limit"] = limit or 100
                bind_vars["skip"] = skip or 0

                if self._client.db is None:
                    raise RuntimeError("ArangoDB client is not connected")

                result = self._client.execute_aql(aql, bind_vars=bind_vars)
                docs = result.get("results", [])
            else:
                # 只查詢全局共享
                filters["tenant_id"] = None
                docs = self._collection.find(filters, skip=skip, limit=limit)

            return [_document_to_model(doc) for doc in docs]
        except Exception as exc:
            self._logger.error("ontology_list_failed", tenant_id=tenant_id, error=str(exc))
            raise

    def update_ontology(
        self, ontology_id: str, updates: OntologyUpdate, tenant_id: Optional[str] = None
    ) -> OntologyModel:
        """
        更新 Ontology

        Args:
            ontology_id: Ontology ID
            updates: 更新數據
            tenant_id: 租戶 ID（用於驗證）

        Returns:
            更新後的 OntologyModel
        """
        try:
            doc = self._collection.get(ontology_id)
            if not doc:
                raise ValueError(f"Ontology not found: {ontology_id}")

            # 驗證租戶隔離
            if tenant_id is not None and doc.get("tenant_id") not in [tenant_id, None]:
                raise PermissionError(
                    f"Access denied: ontology {ontology_id} does not belong to tenant {tenant_id}"
                )

            # 更新字段
            update_data: Dict[str, Any] = {
                "_key": ontology_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if updates.description is not None:
                update_data["description"] = updates.description
            if updates.tags is not None:
                update_data["tags"] = updates.tags
            if updates.use_cases is not None:
                update_data["use_cases"] = updates.use_cases
            if updates.entity_classes is not None:
                update_data["entity_classes"] = updates.entity_classes
            if updates.object_properties is not None:
                update_data["object_properties"] = updates.object_properties
            if updates.metadata is not None:
                update_data["metadata"] = updates.metadata
            if updates.is_active is not None:
                update_data["is_active"] = updates.is_active
            if updates.default_version is not None:
                update_data["default_version"] = updates.default_version
            # WBS-4.2.1: 數據分類與標記
            if updates.data_classification is not None:
                update_data["data_classification"] = updates.data_classification
            if updates.sensitivity_labels is not None:
                update_data["sensitivity_labels"] = updates.sensitivity_labels

            result = self._collection.update(update_data, return_new=True)
            updated_doc = result.get("new") or update_data
            self._logger.info("ontology_updated", id=ontology_id, tenant_id=tenant_id)
            return _document_to_model(updated_doc)
        except Exception as exc:
            self._logger.error("ontology_update_failed", id=ontology_id, error=str(exc))
            raise

    def delete_ontology(
        self, ontology_id: str, tenant_id: Optional[str] = None, hard_delete: bool = False
    ) -> bool:
        """
        刪除 Ontology

        Args:
            ontology_id: Ontology ID
            tenant_id: 租戶 ID（用於驗證）
            hard_delete: 是否硬刪除，False 則軟刪除（設置 is_active=False）

        Returns:
            是否成功
        """
        try:
            doc = self._collection.get(ontology_id)
            if not doc:
                return False

            # 驗證租戶隔離
            if tenant_id is not None and doc.get("tenant_id") not in [tenant_id, None]:
                raise PermissionError(
                    f"Access denied: ontology {ontology_id} does not belong to tenant {tenant_id}"
                )

            if hard_delete:
                self._collection.delete(ontology_id)
                self._logger.info("ontology_deleted_hard", id=ontology_id, tenant_id=tenant_id)
            else:
                # 軟刪除
                self._collection.update({"_key": ontology_id, "is_active": False})
                self._logger.info("ontology_deleted_soft", id=ontology_id, tenant_id=tenant_id)
            return True
        except Exception as exc:
            self._logger.error("ontology_delete_failed", id=ontology_id, error=str(exc))
            raise

    def list_ontology_versions(
        self, name: str, tenant_id: Optional[str] = None
    ) -> List[OntologyModel]:
        """
        列表查詢所有版本

        Args:
            name: Ontology 名稱
            tenant_id: 租戶 ID

        Returns:
            OntologyModel 列表
        """
        try:
            filters: Dict[str, Any] = {"name": name, "is_active": True}
            if tenant_id is not None:
                filters["tenant_id"] = tenant_id
            else:
                filters["tenant_id"] = None

            docs = self._collection.find(filters, sort=["-version"])
            return [_document_to_model(doc) for doc in docs]
        except Exception as exc:
            self._logger.error(
                "ontology_list_versions_failed", name=name, tenant_id=tenant_id, error=str(exc)
            )
            raise

    def set_default_version(self, name: str, version: str, tenant_id: Optional[str] = None) -> bool:
        """
        設置默認版本

        Args:
            name: Ontology 名稱
            version: 版本號
            tenant_id: 租戶 ID

        Returns:
            是否成功
        """
        try:
            # 先將所有版本設置為非默認
            filters: Dict[str, Any] = {"name": name, "is_active": True}
            if tenant_id is not None:
                filters["tenant_id"] = tenant_id
            else:
                filters["tenant_id"] = None

            all_versions = self._collection.find(filters)
            for doc in all_versions:
                if doc.get("default_version"):
                    self._collection.update({"_key": doc["_key"], "default_version": False})

            # 設置指定版本為默認
            ontology_key = _generate_ontology_key(
                all_versions[0].get("type", "base"), name, version, tenant_id
            )
            self._collection.update({"_key": ontology_key, "default_version": True})
            self._logger.info(
                "ontology_default_version_set", name=name, version=version, tenant_id=tenant_id
            )
            return True
        except Exception as exc:
            self._logger.error(
                "ontology_set_default_version_failed",
                name=name,
                version=version,
                tenant_id=tenant_id,
                error=str(exc),
            )
            raise

    def _load_ontology_name_mapping(self) -> Dict[str, Dict[str, str]]:
        """
        從 ontology_list.json 載入文件名到 ontology_name 的映射

        Returns:
            包含 'domain' 和 'major' 兩個鍵的字典，每個鍵對應一個文件名到ontology_name的映射
        """
        mapping: Dict[str, Dict[str, str]] = {"domain": {}, "major": {}}

        try:
            from pathlib import Path
            import json

            # 嘗試找到 ontology_list.json（相對於項目根目錄）
            # 先嘗試從當前文件所在位置推斷
            current_file = Path(__file__).resolve()
            # 從 services/api/services/ontology_store_service.py 向上找到項目根目錄
            project_root = current_file.parent.parent.parent.parent
            ontology_list_path = project_root / "kag" / "ontology" / "ontology_list.json"

            if not ontology_list_path.exists():
                # 如果找不到，嘗試其他可能的路徑
                self._logger.warning(
                    "ontology_list_file_not_found",
                    path=str(ontology_list_path),
                    message="無法找到 ontology_list.json，將使用fallback匹配策略",
                )
                return mapping

            with open(ontology_list_path, "r", encoding="utf-8") as f:
                ontology_list = json.load(f)

            # 建立 domain 映射
            for domain in ontology_list.get("domain_ontologies", []):
                file_name = domain.get("file_name", "")
                ontology_name = domain.get("ontology_name", "")
                if file_name and ontology_name:
                    mapping["domain"][file_name] = ontology_name

            # 建立 major 映射
            for major in ontology_list.get("major_ontologies", []):
                file_name = major.get("file_name", "")
                ontology_name = major.get("ontology_name", "")
                if file_name and ontology_name:
                    mapping["major"][file_name] = ontology_name

            self._logger.debug(
                "ontology_mapping_loaded",
                domain_count=len(mapping["domain"]),
                major_count=len(mapping["major"]),
            )

        except Exception as exc:
            self._logger.warning(
                "failed_to_load_ontology_mapping",
                error=str(exc),
                message="載入 ontology_list.json 失敗，將使用fallback匹配策略",
            )

        return mapping

    def _find_ontology_by_file_or_name(
        self,
        file_name: str,
        ontology_type: str,
        tenant_id: Optional[str],
        mapping: Dict[str, Dict[str, str]],
    ) -> Optional["OntologyModel"]:
        """
        根據文件名或映射的ontology_name查找Ontology

        Args:
            file_name: Ontology文件名（如 "domain-enterprise.json"）
            ontology_type: Ontology類型（"domain" 或 "major"）
            tenant_id: 租戶ID
            mapping: 文件名到ontology_name的映射

        Returns:
            找到的OntologyModel，如果未找到則返回None
        """
        # 策略1: 通過映射的ontology_name查找
        type_mapping = mapping.get(ontology_type, {})
        ontology_name_from_mapping = type_mapping.get(file_name)

        if ontology_name_from_mapping:
            # 從ontology_name提取name（例如 "Enterprise_Domain_Ontology" -> "Enterprise"）
            # 但實際上，我們需要使用ontology_name來查找
            # 讓我們先嘗試通過ontology_name查找
            all_ontologies = self.list_ontologies(
                tenant_id=tenant_id, type=ontology_type, is_active=True
            )

            for ontology in all_ontologies:
                if ontology.ontology_name == ontology_name_from_mapping:
                    return ontology

            # 如果通過ontology_name找不到，嘗試通過name查找
            # 從ontology_name推斷name（例如 "Enterprise_Domain_Ontology" -> "Enterprise"）
            name_candidates = [
                ontology_name_from_mapping.replace("_Domain_Ontology", ""),
                ontology_name_from_mapping.replace("_Major_Ontology", ""),
                ontology_name_from_mapping,
            ]

            for name_candidate in name_candidates:
                ontology = self.get_ontology_with_priority(
                    name_candidate, ontology_type, tenant_id
                )
                if ontology:
                    return ontology

        # 策略2: Fallback - 如果只有一個同類型的Ontology，直接使用它
        all_ontologies = self.list_ontologies(
            tenant_id=tenant_id, type=ontology_type, is_active=True
        )

        if len(all_ontologies) == 1:
            self._logger.debug(
                "using_fallback_ontology",
                file_name=file_name,
                ontology_type=ontology_type,
                ontology_name=all_ontologies[0].ontology_name,
                message="使用fallback策略：只有一個同類型的Ontology，直接使用",
            )
            return all_ontologies[0]

        # 策略3: 嘗試在文件名和Ontology name之間進行模糊匹配
        # 例如: "domain-ai-box.json" -> "AI_Box"
        file_name_lower = file_name.lower().replace(".json", "")
        for ontology in all_ontologies:
            # 提取文件名中的關鍵部分（去掉prefix）
            key_part = file_name_lower
            if file_name_lower.startswith("domain-"):
                key_part = file_name_lower.replace("domain-", "")
            elif file_name_lower.startswith("major-"):
                key_part = file_name_lower.replace("major-", "")

            # 將key_part轉換為可能的name格式（例如 "ai-box" -> "ai_box" 或 "AI_Box"）
            name_variations = [
                key_part.replace("-", "_"),
                key_part.replace("-", "_").title().replace("_", ""),
                key_part.replace("-", "_").upper(),
            ]

            ontology_name_lower = ontology.name.lower()
            ontology_name_clean = ontology_name_lower.replace("_", "").replace("-", "")

            for variation in name_variations:
                variation_clean = variation.lower().replace("_", "").replace("-", "")
                if variation_clean == ontology_name_clean:
                    self._logger.debug(
                        "fuzzy_match_found",
                        file_name=file_name,
                        ontology_name=ontology.name,
                        variation=variation,
                    )
                    return ontology

        return None

    def merge_ontologies(
        self,
        domain_files: List[str],
        major_file: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        合併多個 Ontology（模擬現有的 merge_ontologies 邏輯）

        Args:
            domain_files: Domain 文件名列表（如 ["domain-enterprise.json"]）
            major_file: Major 文件名（可選，如 "major-manufacture.json"）
            tenant_id: 租戶 ID

        Returns:
            合併後的 Ontology 規則（entity_classes, relationship_types, owl_domain_range）
        """
        try:
            merged_rules: Dict[str, Any] = {
                "entity_classes": [],
                "relationship_types": [],
                "owl_domain_range": {},
            }

            # 1. 載入 base ontology
            base_ontology = self.get_ontology_with_priority(
                "5W1H_Base_Ontology_OWL", "base", tenant_id
            )
            if base_ontology:
                all_entities = set()
                # 處理 entity_classes
                for ec in base_ontology.entity_classes:
                    if isinstance(ec, dict):
                        all_entities.add(ec.get("name", ""))
                    else:
                        all_entities.add(ec.name if hasattr(ec, "name") else str(ec))

                # 處理 object_properties
                for op in base_ontology.object_properties:
                    op_dict = (
                        op
                        if isinstance(op, dict)
                        else op.model_dump() if hasattr(op, "model_dump") else {}
                    )
                    rel_name = op_dict.get("name", "")
                    if rel_name:
                        merged_rules["relationship_types"].append(rel_name)

                        if rel_name not in merged_rules["owl_domain_range"]:
                            merged_rules["owl_domain_range"][rel_name] = []

                        for domain_type in op_dict.get("domain", []):
                            for range_type in op_dict.get("range", []):
                                merged_rules["owl_domain_range"][rel_name].append(
                                    (domain_type, range_type)
                                )

                merged_rules["entity_classes"] = list(all_entities)

            # 載入文件名到ontology_name的映射
            file_name_mapping = self._load_ontology_name_mapping()

            # 2. 載入 domain ontologies
            for domain_file in domain_files:
                # 使用新的查找方法
                domain_ontology = self._find_ontology_by_file_or_name(
                    domain_file, "domain", tenant_id, file_name_mapping
                )

                if domain_ontology:
                    # 合併實體和關係
                    for ec in domain_ontology.entity_classes:
                        ec_dict = (
                            ec
                            if isinstance(ec, dict)
                            else ec.model_dump() if hasattr(ec, "model_dump") else {}
                        )
                        entity_name = ec_dict.get("name", "")
                        if entity_name:
                            merged_rules["entity_classes"].append(entity_name)

                    for op in domain_ontology.object_properties:
                        op_dict = (
                            op
                            if isinstance(op, dict)
                            else op.model_dump() if hasattr(op, "model_dump") else {}
                        )
                        rel_name = op_dict.get("name", "")
                        if rel_name and rel_name not in merged_rules["relationship_types"]:
                            merged_rules["relationship_types"].append(rel_name)

                        if rel_name not in merged_rules["owl_domain_range"]:
                            merged_rules["owl_domain_range"][rel_name] = []

                        for domain_type in op_dict.get("domain", []):
                            for range_type in op_dict.get("range", []):
                                merged_rules["owl_domain_range"][rel_name].append(
                                    (domain_type, range_type)
                                )
                else:
                    self._logger.warning(
                        "domain_ontology_not_found",
                        file_name=domain_file,
                        message=f"未找到匹配的domain ontology: {domain_file}",
                    )

            # 3. 載入 major ontology（如果提供）
            if major_file:
                # 使用新的查找方法
                major_ontology = self._find_ontology_by_file_or_name(
                    major_file, "major", tenant_id, file_name_mapping
                )

                if major_ontology:
                    # 合併實體和關係
                    for ec in major_ontology.entity_classes:
                        ec_dict = (
                            ec
                            if isinstance(ec, dict)
                            else ec.model_dump() if hasattr(ec, "model_dump") else {}
                        )
                        entity_name = ec_dict.get("name", "")
                        if entity_name:
                            merged_rules["entity_classes"].append(entity_name)

                    for op in major_ontology.object_properties:
                        op_dict = (
                            op
                            if isinstance(op, dict)
                            else op.model_dump() if hasattr(op, "model_dump") else {}
                        )
                        rel_name = op_dict.get("name", "")
                        if rel_name and rel_name not in merged_rules["relationship_types"]:
                            merged_rules["relationship_types"].append(rel_name)

                        if rel_name not in merged_rules["owl_domain_range"]:
                            merged_rules["owl_domain_range"][rel_name] = []

                        for domain_type in op_dict.get("domain", []):
                            for range_type in op_dict.get("range", []):
                                merged_rules["owl_domain_range"][rel_name].append(
                                    (domain_type, range_type)
                                )
                else:
                    self._logger.warning(
                        "major_ontology_not_found",
                        file_name=major_file,
                        message=f"未找到匹配的major ontology: {major_file}",
                    )

            # 去重
            merged_rules["entity_classes"] = list(set(merged_rules["entity_classes"]))
            merged_rules["relationship_types"] = list(set(merged_rules["relationship_types"]))

            self._logger.info(
                "ontologies_merged",
                domain_count=len(domain_files),
                major_file=major_file,
                entity_count=len(merged_rules["entity_classes"]),
                relationship_count=len(merged_rules["relationship_types"]),
            )

            return merged_rules
        except Exception as exc:
            self._logger.error("ontology_merge_failed", error=str(exc))
            raise


_service: Optional[OntologyStoreService] = None


def get_ontology_store_service() -> OntologyStoreService:
    """獲取 OntologyStoreService 單例"""
    global _service
    if _service is None:
        _service = OntologyStoreService()
    return _service
