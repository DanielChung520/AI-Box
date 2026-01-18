# 代碼功能說明: Config 存儲服務 - 提供 Config 的 CRUD 操作和多層級配置合併
# 創建日期: 2025-12-18 19:39:14 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-29

"""Config Store Service

提供 Config 的 CRUD 操作，支援 system/tenant/user 三層配置和合併邏輯。
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from database.arangodb import ArangoCollection, ArangoDBClient
from services.api.models.config import ConfigCreate, ConfigModel, ConfigUpdate, EffectiveConfig
from services.api.models.version_history import VersionHistoryCreate

logger = structlog.get_logger(__name__)

SYSTEM_CONFIGS_COLLECTION = "system_configs"
TENANT_CONFIGS_COLLECTION = "tenant_configs"
USER_CONFIGS_COLLECTION = "user_configs"


def _generate_config_key(
    scope: str, tenant_id: Optional[str] = None, user_id: Optional[str] = None
) -> str:
    """生成 Config 的 _key"""
    if user_id:
        return f"{tenant_id}_{user_id}_{scope}"
    elif tenant_id:
        return f"{tenant_id}_{scope}"
    else:
        return scope


def _normalize_provider(value: str) -> str:
    """標準化 provider 名稱"""
    return str(value).strip().lower()


def _pattern_is_subset_of_any(pattern: str, supersets: List[str]) -> bool:
    """判斷 pattern 是否不會擴權（是否被 system pattern 覆蓋）"""
    p = str(pattern).strip().lower()
    if not p:
        return False
    for s in supersets:
        sp = str(s).strip().lower()
        if not sp:
            continue
        if sp == "*":
            return True
        if sp.endswith("*"):
            # system: gpt-* 覆蓋 tenant: gpt-4o / gpt-4* / gpt-4o-mini
            if p.startswith(sp[:-1]):
                return True
        else:
            # system exact
            if p == sp:
                return True
    return False


def _document_to_model(doc: Dict[str, Any], collection_name: str) -> ConfigModel:
    """將 ArangoDB document 轉換為 ConfigModel"""
    return ConfigModel(
        id=doc.get("_key"),
        tenant_id=doc.get("tenant_id"),
        user_id=doc.get("user_id") if collection_name == USER_CONFIGS_COLLECTION else None,
        scope=doc.get("scope"),
        sub_scope=doc.get("sub_scope"),
        category=doc.get("category"),
        is_active=doc.get("is_active", True),
        config_data=doc.get("config_data", {}),
        metadata=doc.get("metadata", {}),
        # WBS-4.2.1: 數據分類與標記
        data_classification=doc.get("data_classification"),
        sensitivity_labels=doc.get("sensitivity_labels"),
        created_at=datetime.fromisoformat(doc["created_at"]) if doc.get("created_at") else None,
        updated_at=datetime.fromisoformat(doc["updated_at"]) if doc.get("updated_at") else None,
        created_by=doc.get("created_by"),
        updated_by=doc.get("updated_by"),
    )


class ConfigStoreService:
    """Config 存儲服務"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """
        初始化 Config Store Service

        Args:
            client: ArangoDB 客戶端，如果為 None 則創建新實例
        """
        self._client = client or ArangoDBClient()
        self._logger = logger

        if self._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 確保 collections 存在
        system_collection = self._client.get_or_create_collection(SYSTEM_CONFIGS_COLLECTION)
        tenant_collection = self._client.get_or_create_collection(TENANT_CONFIGS_COLLECTION)
        user_collection = self._client.get_or_create_collection(USER_CONFIGS_COLLECTION)

        self._system_collection = ArangoCollection(system_collection)
        self._tenant_collection = ArangoCollection(tenant_collection)
        self._user_collection = ArangoCollection(user_collection)

        # 延遲初始化版本歷史服務（可選）
        self._version_history_service: Optional[Any] = None

    def save_config(
        self,
        config: ConfigCreate,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> str:
        """
        保存配置（system/tenant/user）

        Args:
            config: Config 創建數據
            tenant_id: 租戶 ID（覆寫 config.tenant_id）
            user_id: 用戶 ID（覆寫 config.user_id）
            changed_by: 變更者（用戶 ID），用於版本歷史記錄（可選）

        Returns:
            Config ID
        """
        final_tenant_id = tenant_id or config.tenant_id
        final_user_id = user_id or config.user_id

        # 確定使用哪個 collection
        if final_user_id:
            collection = self._user_collection
        elif final_tenant_id:
            collection = self._tenant_collection
        else:
            collection = self._system_collection

        config_key = _generate_config_key(config.scope, final_tenant_id, final_user_id)
        now = datetime.utcnow().isoformat()

        # 獲取舊版本數據（用於版本歷史記錄）
        existing = collection.get(config_key)
        previous_version_data: Dict[str, Any] = {}
        if existing:
            # 複製現有數據作為舊版本
            previous_version_data = dict(existing)

        doc: Dict[str, Any] = {
            "_key": config_key,
            "tenant_id": final_tenant_id,
            "scope": config.scope,
            "sub_scope": config.sub_scope,
            "category": config.category,
            "is_active": True,
            "config_data": config.config_data,
            "metadata": config.metadata or {},
            # WBS-4.2.1: 數據分類與標記
            "data_classification": config.data_classification,
            "sensitivity_labels": config.sensitivity_labels,
            "created_at": now,
            "updated_at": now,
        }

        if final_user_id:
            doc["user_id"] = final_user_id

        try:
            if existing:
                # 更新
                doc["created_at"] = existing.get("created_at", now)
                doc["_key"] = existing.get("_key", config_key)
                collection.update(doc)
                self._logger.info(
                    "config_updated",
                    id=config_key,
                    scope=config.scope,
                    tenant_id=final_tenant_id,
                    user_id=final_user_id,
                )
                change_type = "update"
            else:
                # 創建
                collection.insert(doc)
                self._logger.info(
                    "config_created",
                    id=config_key,
                    scope=config.scope,
                    tenant_id=final_tenant_id,
                    user_id=final_user_id,
                )
                change_type = "create"

            # 記錄版本歷史（可選，失敗不影響主流程）
            if changed_by:
                self._record_version_history(
                    resource_type="configs",
                    resource_id=config_key,
                    change_type=change_type,
                    changed_by=changed_by,
                    previous_version=previous_version_data,
                    current_version=doc,
                    scope=config.scope,
                )

            return config_key
        except Exception as exc:
            self._logger.error("config_save_failed", id=config_key, error=str(exc))
            raise

    def _record_version_history(
        self,
        resource_type: str,
        resource_id: str,
        change_type: str,
        changed_by: str,
        previous_version: Dict[str, Any],
        current_version: Dict[str, Any],
        scope: Optional[str] = None,
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
            change_summary = f"{change_type.title()} config"
            if scope:
                change_summary += f": {scope}"

            version_data = VersionHistoryCreate(
                resource_type=resource_type,
                resource_id=resource_id,
                change_type=change_type,
                changed_by=changed_by,
                change_summary=change_summary,
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

    def get_config(
        self,
        scope: str,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[ConfigModel]:
        """
        獲取單層配置

        Args:
            scope: 配置範圍
            tenant_id: 租戶 ID（None 表示 system）
            user_id: 用戶 ID（None 表示 tenant 或 system）

        Returns:
            ConfigModel 或 None
        """
        try:
            if user_id:
                collection = self._user_collection
                collection_name = USER_CONFIGS_COLLECTION
                config_key = _generate_config_key(scope, tenant_id, user_id)
            elif tenant_id:
                collection = self._tenant_collection
                collection_name = TENANT_CONFIGS_COLLECTION
                config_key = _generate_config_key(scope, tenant_id)
            else:
                collection = self._system_collection
                collection_name = SYSTEM_CONFIGS_COLLECTION
                config_key = _generate_config_key(scope)

            doc = collection.get(config_key)
            if not doc:
                return None

            return _document_to_model(doc, collection_name)
        except Exception as exc:
            self._logger.error(
                "config_get_failed",
                scope=scope,
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(exc),
            )
            raise

    def get_effective_config(
        self, scope: str, tenant_id: str, user_id: Optional[str] = None
    ) -> EffectiveConfig:
        """
        獲取有效配置（合併 system → tenant → user）

        Args:
            scope: 配置範圍
            tenant_id: 租戶 ID
            user_id: 用戶 ID（可選）

        Returns:
            EffectiveConfig
        """
        try:
            # 1. 獲取 system 配置
            system_config = self.get_config(scope, tenant_id=None, user_id=None)
            system_data = system_config.config_data if system_config else {}

            # 2. 獲取 tenant 配置
            tenant_config = self.get_config(scope, tenant_id=tenant_id, user_id=None)
            tenant_data = tenant_config.config_data if tenant_config else None

            # 3. 獲取 user 配置
            user_data = None
            if user_id:
                user_config = self.get_config(scope, tenant_id=tenant_id, user_id=user_id)
                user_data = user_config.config_data if user_config else None

            # 4. 合併配置
            merged_config = self._merge_configs(system_data, tenant_data, user_data)

            merged_from = {
                "system": system_config is not None,
                "tenant": tenant_config is not None,
                "user": user_config is not None if user_id else False,
            }

            return EffectiveConfig(
                scope=scope,
                tenant_id=tenant_id,
                user_id=user_id,
                config=merged_config,
                merged_from=merged_from,
            )
        except Exception as exc:
            self._logger.error(
                "effective_config_get_failed",
                scope=scope,
                tenant_id=tenant_id,
                user_id=user_id,
                error=str(exc),
            )
            raise

    def _merge_configs(
        self,
        system_config: Dict[str, Any],
        tenant_config: Optional[Dict[str, Any]],
        user_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        合併配置邏輯（實現收斂規則）

        Args:
            system_config: System 層配置
            tenant_config: Tenant 層配置（可選）
            user_config: User 層配置（可選）

        Returns:
            合併後的配置
        """
        # 先以 system 配置為底
        merged: Dict[str, Any] = dict(system_config)

        # tenant 配置只能收斂（不擴權）
        if tenant_config:
            # allowed_providers: 交集運算
            sys_allowed_providers = [
                _normalize_provider(p) for p in merged.get("allowed_providers", [])
            ]
            tenant_allowed_providers = [
                _normalize_provider(p) for p in tenant_config.get("allowed_providers", [])
            ]

            if tenant_allowed_providers:
                if sys_allowed_providers:
                    merged["allowed_providers"] = [
                        p for p in tenant_allowed_providers if p in sys_allowed_providers
                    ]
                else:
                    merged["allowed_providers"] = tenant_allowed_providers

            # allowed_models: 每個 provider 的模式列表交集
            sys_allowed_models = merged.get("allowed_models", {})
            tenant_allowed_models = tenant_config.get("allowed_models", {})
            if isinstance(sys_allowed_models, dict) and tenant_allowed_models:
                new_allowed_models: Dict[str, List[str]] = dict(sys_allowed_models)
                for prov, patterns in tenant_allowed_models.items():
                    prov_key = _normalize_provider(prov)
                    if not prov_key or not isinstance(patterns, list):
                        continue
                    sys_patterns_raw = sys_allowed_models.get(prov_key)
                    sys_patterns = (
                        [str(x).strip() for x in sys_patterns_raw]
                        if isinstance(sys_patterns_raw, list)
                        else []
                    )
                    # 只接受被 system 覆蓋的 patterns
                    filtered = [
                        str(p).strip()
                        for p in patterns
                        if str(p).strip()
                        and (not sys_patterns or _pattern_is_subset_of_any(str(p), sys_patterns))
                    ]
                    new_allowed_models[prov_key] = filtered
                merged["allowed_models"] = new_allowed_models

            # default_fallback: 允許 tenant 覆蓋
            if "default_fallback" in tenant_config:
                merged["default_fallback"] = tenant_config["default_fallback"]

            # 其他字段：直接合併（tenant 可以覆蓋）
            for key, value in tenant_config.items():
                if key not in ["allowed_providers", "allowed_models", "default_fallback"]:
                    merged[key] = value

        # user 配置優先級最高（可以覆蓋任何配置）
        if user_config:
            merged.update(user_config)

        return merged

    def _validate_config_convergence(
        self, system_config: Dict[str, Any], tenant_config: Dict[str, Any]
    ) -> bool:
        """
        驗證配置收斂（tenant 不能擴權）

        Args:
            system_config: System 層配置
            tenant_config: Tenant 層配置

        Returns:
            是否符合收斂規則
        """
        # 檢查 allowed_providers
        sys_providers = set(
            _normalize_provider(p) for p in system_config.get("allowed_providers", [])
        )
        tenant_providers = set(
            _normalize_provider(p) for p in tenant_config.get("allowed_providers", [])
        )
        if tenant_providers - sys_providers:
            return False

        # 檢查 allowed_models
        sys_models = system_config.get("allowed_models", {})
        tenant_models = tenant_config.get("allowed_models", {})
        if isinstance(sys_models, dict) and isinstance(tenant_models, dict):
            for prov, patterns in tenant_models.items():
                prov_key = _normalize_provider(prov)
                sys_patterns = sys_models.get(prov_key, [])
                tenant_patterns_list = patterns if isinstance(patterns, list) else []
                for pattern in tenant_patterns_list:
                    if not _pattern_is_subset_of_any(str(pattern), sys_patterns):
                        return False

        return True

    def update_config(
        self,
        config_id: str,
        updates: ConfigUpdate,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> ConfigModel:
        """
        更新配置

        Args:
            config_id: Config ID
            updates: 更新數據
            tenant_id: 租戶 ID（用於驗證）
            user_id: 用戶 ID（用於驗證）

        Returns:
            更新後的 ConfigModel
        """
        try:
            # 確定使用哪個 collection
            if user_id:
                collection = self._user_collection
                collection_name = USER_CONFIGS_COLLECTION
            elif tenant_id:
                collection = self._tenant_collection
                collection_name = TENANT_CONFIGS_COLLECTION
            else:
                collection = self._system_collection
                collection_name = SYSTEM_CONFIGS_COLLECTION

            doc = collection.get(config_id)
            if not doc:
                raise ValueError(f"Config not found: {config_id}")

            # 驗證租戶隔離
            if tenant_id is not None and doc.get("tenant_id") != tenant_id:
                raise PermissionError(
                    f"Access denied: config {config_id} does not belong to tenant {tenant_id}"
                )

            # 如果是 tenant 配置，驗證收斂規則
            if tenant_id and updates.config_data:
                scope = doc.get("scope")
                if not scope or not isinstance(scope, str):
                    raise ValueError("scope must be a string")
                system_config = self.get_config(scope, tenant_id=None, user_id=None)  # type: ignore[arg-type]  # 已檢查為 str
                if system_config:
                    if not self._validate_config_convergence(
                        system_config.config_data, updates.config_data
                    ):
                        raise ValueError("Tenant config violates convergence rules")

            # 更新字段
            update_data: Dict[str, Any] = {
                "_key": config_id,
                "updated_at": datetime.utcnow().isoformat(),
            }
            if updates.config_data is not None:
                update_data["config_data"] = updates.config_data
            if updates.metadata is not None:
                update_data["metadata"] = updates.metadata
            if updates.is_active is not None:
                update_data["is_active"] = updates.is_active
            # WBS-4.2.1: 數據分類與標記
            if updates.data_classification is not None:
                update_data["data_classification"] = updates.data_classification
            if updates.sensitivity_labels is not None:
                update_data["sensitivity_labels"] = updates.sensitivity_labels

            result = collection.update(update_data, return_new=True)
            updated_doc = result.get("new") or update_data
            self._logger.info(
                "config_updated",
                id=config_id,
                scope=doc.get("scope"),
                tenant_id=tenant_id,
                user_id=user_id,
            )
            return _document_to_model(updated_doc, collection_name)
        except Exception as exc:
            self._logger.error("config_update_failed", id=config_id, error=str(exc))
            raise

    def delete_config(
        self,
        config_id: str,
        tenant_id: Optional[str] = None,
        hard_delete: bool = False,
    ) -> bool:
        """
        刪除配置

        Args:
            config_id: Config ID
            tenant_id: 租戶 ID（用於驗證）
            hard_delete: 是否硬刪除，False 則軟刪除（設置 is_active=False）

        Returns:
            是否成功
        """
        try:
            # 嘗試從各個 collection 查找
            doc = None
            collection = None

            for coll_name, coll in [
                (SYSTEM_CONFIGS_COLLECTION, self._system_collection),
                (TENANT_CONFIGS_COLLECTION, self._tenant_collection),
                (USER_CONFIGS_COLLECTION, self._user_collection),
            ]:
                doc = coll.get(config_id)
                if doc:
                    collection = coll
                    break

            if not doc or not collection:
                return False

            # 驗證租戶隔離
            if tenant_id is not None and doc.get("tenant_id") != tenant_id:
                raise PermissionError(
                    f"Access denied: config {config_id} does not belong to tenant {tenant_id}"
                )

            if hard_delete:
                collection.delete(config_id)
                self._logger.info("config_deleted_hard", id=config_id, tenant_id=tenant_id)
            else:
                # 軟刪除
                collection.update({"_key": config_id, "is_active": False})
                self._logger.info("config_deleted_soft", id=config_id, tenant_id=tenant_id)
            return True
        except Exception as exc:
            self._logger.error("config_delete_failed", id=config_id, error=str(exc))
            raise


_service: Optional["ConfigStoreService"] = None


def get_config_store_service() -> "ConfigStoreService":
    """獲取 ConfigStoreService 單例"""
    global _service
    if _service is None:
        _service = ConfigStoreService()
    return _service
