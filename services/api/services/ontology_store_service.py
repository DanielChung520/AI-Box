# 代碼功能說明: Ontology 存儲服務 - 提供 Ontology 的 CRUD 操作和多租戶支援
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-18 19:39:14 (UTC+8)

"""Ontology Store Service

提供 Ontology 的 CRUD 操作，支援多租戶隔離和版本控制。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.ontology import OntologyCreate, OntologyModel, OntologyUpdate

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

    def save_ontology(self, ontology: OntologyCreate, tenant_id: Optional[str] = None) -> str:
        """
        保存 Ontology（創建或更新）

        Args:
            ontology: Ontology 創建數據
            tenant_id: 租戶 ID，如果為 None 則使用 ontology.tenant_id

        Returns:
            Ontology ID
        """
        final_tenant_id = tenant_id or ontology.tenant_id
        ontology_key = _generate_ontology_key(
            ontology.type, ontology.name, ontology.version, final_tenant_id
        )

        now = datetime.utcnow().isoformat()
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
            existing = self._collection.get(ontology_key)
            if existing:
                # 更新
                doc["created_at"] = existing.get("created_at", now)
                doc["_key"] = existing.get("_key", ontology_key)
                self._collection.update(doc)
                self._logger.info("ontology_updated", id=ontology_key, tenant_id=final_tenant_id)
            else:
                # 創建
                self._collection.insert(doc)
                self._logger.info("ontology_created", id=ontology_key, tenant_id=final_tenant_id)
            return ontology_key
        except Exception as exc:
            self._logger.error("ontology_save_failed", id=ontology_key, error=str(exc))
            raise

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

                aql += " LIMIT @limit OFFSET @skip RETURN doc"
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
                        else op.model_dump()
                        if hasattr(op, "model_dump")
                        else {}
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

            # 2. 載入 domain ontologies
            for domain_file in domain_files:
                # 從文件名提取 ontology_name（需要從實際數據中獲取）
                # 這裡簡化處理，使用文件名推斷
                domain_ontologies = self.list_ontologies(
                    tenant_id=tenant_id, type="domain", is_active=True
                )
                # 查找匹配的 domain ontology（根據文件名或名稱）
                for domain_ontology in domain_ontologies:
                    if any(
                        domain_file in f
                        for f in [domain_ontology.name, domain_ontology.ontology_name]
                    ):
                        # 合併實體和關係
                        for ec in domain_ontology.entity_classes:
                            ec_dict = (
                                ec
                                if isinstance(ec, dict)
                                else ec.model_dump()
                                if hasattr(ec, "model_dump")
                                else {}
                            )
                            entity_name = ec_dict.get("name", "")
                            if entity_name:
                                merged_rules["entity_classes"].append(entity_name)

                        for op in domain_ontology.object_properties:
                            op_dict = (
                                op
                                if isinstance(op, dict)
                                else op.model_dump()
                                if hasattr(op, "model_dump")
                                else {}
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
                        break

            # 3. 載入 major ontology（如果提供）
            if major_file:
                major_ontologies = self.list_ontologies(
                    tenant_id=tenant_id, type="major", is_active=True
                )
                for major_ontology in major_ontologies:
                    if any(
                        major_file in f for f in [major_ontology.name, major_ontology.ontology_name]
                    ):
                        # 合併實體和關係
                        for ec in major_ontology.entity_classes:
                            ec_dict = (
                                ec
                                if isinstance(ec, dict)
                                else ec.model_dump()
                                if hasattr(ec, "model_dump")
                                else {}
                            )
                            entity_name = ec_dict.get("name", "")
                            if entity_name:
                                merged_rules["entity_classes"].append(entity_name)

                        for op in major_ontology.object_properties:
                            op_dict = (
                                op
                                if isinstance(op, dict)
                                else op.model_dump()
                                if hasattr(op, "model_dump")
                                else {}
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
                        break

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
