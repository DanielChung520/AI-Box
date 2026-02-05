# 代碼功能說明: 系統參數管理路由
# 創建日期: 2026-01-17 17:36 UTC+8
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-18 11:15 UTC+8

"""系統參數管理路由 - 提供系統配置的 CRUD API"""

from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Body, Depends, Path, Query, status
from fastapi.responses import JSONResponse

from api.core.response import APIResponse
from services.api.models.audit_log import AuditAction
from services.api.models.config import ConfigCreate, ConfigUpdate
from services.api.services.config_store_service import ConfigStoreService
from system.security.audit_decorator import audit_log
from system.security.dependencies import get_current_user
from system.security.models import Permission, User

logger = structlog.get_logger(__name__)


# 創建需要系統管理員權限的依賴函數
async def require_system_admin(user: User = Depends(get_current_user)) -> User:
    """檢查用戶是否擁有系統管理員權限的依賴函數（修改時間：2026-01-18）"""
    from fastapi import HTTPException

    from system.security.config import get_security_settings

    settings = get_security_settings()

    # 開發模式下自動通過權限檢查
    if settings.should_bypass_auth:
        return user

    # 生產模式下進行真實權限檢查
    if not settings.rbac.enabled:
        # 如果 RBAC 未啟用，則所有已認證用戶都可以訪問
        return user

    if not user.has_permission(Permission.ALL.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: system_admin",
        )

    return user


router = APIRouter(prefix="/admin/system-configs", tags=["System Config"])


def get_config_service() -> ConfigStoreService:
    """獲取 Config Store Service 實例"""
    return ConfigStoreService()


@router.get("", status_code=status.HTTP_200_OK)
async def list_system_configs(
    scope: Optional[str] = Query(default=None, description="配置範圍過濾（可選）"),
    category: Optional[str] = Query(
        default=None,
        description="配置分類過濾：basic/feature_flag/performance/security/business（可選）",
    ),
    include_inactive: bool = Query(default=False, description="是否包含未啟用的配置"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取系統配置列表（支持 scope 和 category 過濾）

    Args:
        scope: 配置範圍過濾（可選）
        category: 配置分類過濾（可選）
        include_inactive: 是否包含未啟用的配置
        current_user: 當前認證用戶

    Returns:
        系統配置列表
    """
    try:
        service = get_config_service()

        # 獲取所有系統配置（tenant_id=None 表示系統級）
        if scope:
            # 獲取特定 scope 的配置
            config = service.get_config(scope, tenant_id=None)
            configs = [config] if config else []
        else:
            # 獲取所有系統配置（需要遍歷所有可能的 scope）
            # 由於沒有直接的方法獲取所有配置，我們需要從 collection 中查詢
            if service._client.db is None:
                raise RuntimeError("ArangoDB client is not connected")

            collection = service._client.db.collection("system_configs")
            filters: Dict[str, Any] = {}
            if not include_inactive:
                filters["is_active"] = True
            if category:
                filters["category"] = category

            from services.api.services.config_store_service import _document_to_model

            # 使用 AQL 查詢以提高性能（支持索引）
            aql = """
            FOR doc IN system_configs
            FILTER doc.is_active == true
            """
            bind_vars: Dict[str, Any] = {}

            if category:
                aql += " AND doc.category == @category"
                bind_vars["category"] = category

            aql += " LIMIT 1000 RETURN doc"

            try:
                cursor = service._client.db.aql.execute(aql, bind_vars=bind_vars)
                docs = [doc for doc in cursor]
            except Exception as e:
                # Fallback 到 collection.find
                logger.warning(f"AQL query failed, falling back to collection.find: {str(e)}")
                docs = collection.find(filters, limit=1000)

            configs = [_document_to_model(doc, "system_configs") for doc in docs]

        config_dicts = [config.model_dump(mode="json") for config in configs if config]

        return APIResponse.success(
            data={"configs": config_dicts, "total": len(config_dicts)},
            message="System configs retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list system configs: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list system configs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{scope}", status_code=status.HTTP_200_OK)
async def get_system_config(
    scope: str = Path(description="配置範圍"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取特定 scope 的系統配置

    Args:
        scope: 配置範圍
        current_user: 當前認證用戶

    Returns:
        系統配置詳情
    """
    try:
        service = get_config_service()
        config = service.get_config(scope, tenant_id=None)

        if config is None:
            return APIResponse.error(
                message=f"System config '{scope}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        return APIResponse.success(
            data=config.model_dump(mode="json"),
            message="System config retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to get system config: scope={scope}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get system config: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("", status_code=status.HTTP_201_CREATED)
@audit_log(
    action=AuditAction.CONFIG_CREATE,
    resource_type="system_config",
    get_resource_id=lambda body: body.get("data", {}).get("scope"),
)
async def create_system_config(
    config: ConfigCreate,
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    創建/更新系統配置

    Args:
        config: 配置創建數據
        current_user: 當前認證用戶

    Returns:
        創建的配置信息
    """
    try:
        service = get_config_service()

        # 保存系統配置（tenant_id=None 表示系統級）
        config_id = service.save_config(config, tenant_id=None, changed_by=current_user.user_id)

        # 獲取創建的配置
        created_config = service.get_config(config.scope, tenant_id=None)

        logger.info(f"System config created: scope={config.scope}, id={config_id}")

        return APIResponse.success(
            data=created_config.model_dump(mode="json") if created_config else {},
            message="System config created successfully",
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as e:
        logger.error(
            f"Failed to create system config: scope={config.scope}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to create system config: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.put("/{scope}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.CONFIG_UPDATE,
    resource_type="system_config",
    get_resource_id=lambda scope: scope,
)
async def update_system_config(
    scope: str = Path(description="配置範圍"),
    updates: ConfigUpdate = None,  # type: ignore
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    更新系統配置

    Args:
        scope: 配置範圍
        updates: 更新字段
        current_user: 當前認證用戶

    Returns:
        更新後的配置信息
    """
    try:
        service = get_config_service()

        # 獲取現有配置
        existing_config = service.get_config(scope, tenant_id=None)
        if existing_config is None:
            return APIResponse.error(
                message=f"System config '{scope}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        if updates is None:
            return APIResponse.error(
                message="Updates are required",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # 合併更新
        config_data = (
            updates.config_data if updates.config_data is not None else existing_config.config_data
        )
        metadata = updates.metadata if updates.metadata is not None else existing_config.metadata
        category = updates.category if updates.category is not None else existing_config.category
        is_active = (
            updates.is_active if updates.is_active is not None else existing_config.is_active
        )

        # 創建更新後的配置
        config_update = ConfigCreate(
            scope=scope,
            sub_scope=existing_config.sub_scope,
            category=category,
            config_data=config_data,
            metadata=metadata,
            data_classification=(
                updates.data_classification
                if updates.data_classification is not None
                else existing_config.data_classification
            ),
            sensitivity_labels=(
                updates.sensitivity_labels
                if updates.sensitivity_labels is not None
                else existing_config.sensitivity_labels
            ),
        )

        # 保存更新後的配置
        service.save_config(config_update, tenant_id=None, changed_by=current_user.user_id)

        # 如果 is_active 變更，需要直接更新 collection
        if is_active != existing_config.is_active:
            if service._client.db is None:
                raise RuntimeError("ArangoDB client is not connected")
            collection = service._client.db.collection("system_configs")
            config_key = scope
            doc = collection.get(config_key)
            if doc:
                doc["is_active"] = is_active
                collection.update(doc)

        # 獲取更新後的配置
        updated_config = service.get_config(scope, tenant_id=None)

        logger.info(f"System config updated: scope={scope}")

        return APIResponse.success(
            data=updated_config.model_dump(mode="json") if updated_config else {},
            message="System config updated successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to update system config: scope={scope}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to update system config: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.delete("/{scope}", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.CONFIG_DELETE,
    resource_type="system_config",
    get_resource_id=lambda scope: scope,
)
async def delete_system_config(
    scope: str = Path(description="配置範圍"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    刪除系統配置（軟刪除）

    Args:
        scope: 配置範圍
        current_user: 當前認證用戶

    Returns:
        刪除結果
    """
    try:
        service = get_config_service()

        # 獲取現有配置
        existing_config = service.get_config(scope, tenant_id=None)
        if existing_config is None:
            return APIResponse.error(
                message=f"System config '{scope}' not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        # 軟刪除：設置 is_active = False
        if service._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = service._client.db.collection("system_configs")
        config_key = scope
        doc = collection.get(config_key)
        if doc:
            doc["is_active"] = False
            collection.update(doc)

        logger.info(f"System config deleted: scope={scope}")

        return APIResponse.success(
            data={"scope": scope},
            message="System config deleted successfully",
        )
    except Exception as e:
        logger.error(
            f"Failed to delete system config: scope={scope}, error={str(e)}", exc_info=True
        )
        return APIResponse.error(
            message=f"Failed to delete system config: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/{scope}/history", status_code=status.HTTP_200_OK)
async def get_config_history(
    scope: str = Path(description="配置範圍"),
    limit: Optional[int] = Query(default=100, description="限制返回數量"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取配置變更歷史

    Args:
        scope: 配置範圍
        limit: 限制返回數量
        current_user: 當前認證用戶

    Returns:
        配置變更歷史記錄
    """
    try:
        # 嘗試從版本歷史服務獲取歷史記錄
        try:
            # 獲取配置的版本歷史
            # 注意：version_history_service 的 API 可能需要調整
            # 這裡先返回一個基本實現
            history = []  # TODO: 實現從版本歷史服務獲取歷史記錄

            return APIResponse.success(
                data={"history": history, "total": len(history)},
                message="Config history retrieved successfully",
            )
        except ImportError:
            # 版本歷史服務不可用
            return APIResponse.success(
                data={
                    "history": [],
                    "total": 0,
                    "message": "Version history service not available",
                },
                message="Config history service not available",
            )
    except Exception as e:
        logger.error(f"Failed to get config history: scope={scope}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to get config history: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/{scope}/validate", status_code=status.HTTP_200_OK)
async def validate_config(
    scope: str = Path(description="配置範圍"),
    config_data: Optional[Dict[str, Any]] = Body(default=None, description="要驗證的配置數據（可選）"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    驗證配置參數

    Args:
        scope: 配置範圍
        config_data: 要驗證的配置數據（可選，如果不提供則驗證現有配置）
        current_user: 當前認證用戶

    Returns:
        驗證結果
    """
    try:
        service = get_config_service()

        # 如果提供了 config_data，驗證它；否則驗證現有配置
        if config_data is None:
            existing_config = service.get_config(scope, tenant_id=None)
            if existing_config is None:
                return APIResponse.error(
                    message=f"System config '{scope}' not found",
                    status_code=status.HTTP_404_NOT_FOUND,
                )
            config_data = existing_config.config_data

        # 基本驗證（可以擴展為更複雜的驗證邏輯）
        validation_errors: List[str] = []
        validation_warnings: List[str] = []

        # 驗證配置數據是字典類型
        if not isinstance(config_data, dict):
            validation_errors.append("Config data must be a dictionary/object")

        # 可以添加更多驗證規則
        # 例如：檢查必填字段、類型驗證、範圍驗證等

        is_valid = len(validation_errors) == 0

        return APIResponse.success(
            data={
                "is_valid": is_valid,
                "errors": validation_errors,
                "warnings": validation_warnings,
                "config_data": config_data,
            },
            message="Config validation completed",
        )
    except Exception as e:
        logger.error(f"Failed to validate config: scope={scope}, error={str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to validate config: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/export", status_code=status.HTTP_200_OK)
async def export_configs(
    category: Optional[str] = Query(
        default=None,
        description="配置分類過濾：basic/feature_flag/performance/security/business（可選）",
    ),
    format: str = Query(default="json", description="導出格式：json/yaml"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    導出系統配置

    Args:
        category: 配置分類過濾（可選）
        format: 導出格式（json/yaml）
        current_user: 當前認證用戶

    Returns:
        導出的配置數據
    """
    try:
        service = get_config_service()

        if service._client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        collection = service._client.db.collection("system_configs")
        filters: Dict[str, Any] = {"is_active": True}
        if category:
            filters["category"] = category

        from services.api.services.config_store_service import _document_to_model

        docs = collection.find(filters)
        configs = [_document_to_model(doc, "system_configs") for doc in docs]

        # 轉換為可導出的格式
        export_data = {
            "version": "1.0",
            "exported_at": datetime.utcnow().isoformat(),
            "category": category,
            "total": len(configs),
            "configs": [config.model_dump(mode="json") for config in configs],
        }

        if format.lower() == "yaml":
            try:
                import yaml

                yaml_content = yaml.dump(export_data, default_flow_style=False, allow_unicode=True)
                return JSONResponse(
                    content={"format": "yaml", "data": yaml_content},
                    media_type="text/yaml",
                )
            except ImportError:
                logger.warning("PyYAML not installed, falling back to JSON")
                format = "json"

        # 默認返回 JSON
        return APIResponse.success(
            data={"format": "json", "data": export_data},
            message=f"Successfully exported {len(configs)} configs",
        )
    except Exception as e:
        logger.error(f"Failed to export configs: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to export configs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.post("/import", status_code=status.HTTP_200_OK)
@audit_log(
    action=AuditAction.SYSTEM_ACTION,
    resource_type="system_config",
    get_resource_id=lambda: "import",
)
async def import_configs(
    import_data: Dict[str, Any],
    overwrite: bool = Query(default=False, description="是否覆蓋現有配置"),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    導入系統配置

    Args:
        import_data: 導入的配置數據（JSON 格式）
        overwrite: 是否覆蓋現有配置
        current_user: 當前認證用戶

    Returns:
        導入結果
    """
    try:
        service = get_config_service()

        # 驗證導入數據格式
        if "configs" not in import_data:
            return APIResponse.error(
                message="Invalid import data format: missing 'configs' field",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        configs_data = import_data["configs"]
        imported_count = 0
        skipped_count = 0
        error_count = 0
        errors: List[str] = []

        for config_data in configs_data:
            try:
                # 驗證必填字段
                if "scope" not in config_data:
                    error_count += 1
                    errors.append(
                        f"Config missing 'scope' field: {config_data.get('id', 'unknown')}"
                    )
                    continue

                # 檢查是否已存在
                existing_config = service.get_config(config_data["scope"], tenant_id=None)
                if existing_config and not overwrite:
                    skipped_count += 1
                    continue

                # 創建配置數據
                config_create = ConfigCreate(
                    scope=config_data["scope"],
                    sub_scope=config_data.get("sub_scope"),
                    category=config_data.get("category"),
                    config_data=config_data.get("config_data", {}),
                    metadata=config_data.get("metadata", {}),
                    data_classification=config_data.get("data_classification"),
                    sensitivity_labels=config_data.get("sensitivity_labels"),
                )

                # 保存配置
                service.save_config(config_create, tenant_id=None, changed_by=current_user.user_id)
                imported_count += 1

            except Exception as e:
                error_count += 1
                errors.append(
                    f"Failed to import config {config_data.get('scope', 'unknown')}: {str(e)}"
                )
                logger.warning(
                    f"Failed to import config: {config_data.get('scope', 'unknown')}, error={str(e)}"
                )

        logger.info(
            f"Configs import completed: imported={imported_count}, skipped={skipped_count}, errors={error_count}"
        )

        return APIResponse.success(
            data={
                "imported_count": imported_count,
                "skipped_count": skipped_count,
                "error_count": error_count,
                "errors": errors,
            },
            message=f"Import completed: {imported_count} imported, {skipped_count} skipped, {error_count} errors",
        )
    except Exception as e:
        logger.error(f"Failed to import configs: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to import configs: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@router.get("/templates", status_code=status.HTTP_200_OK)
async def list_config_templates(
    category: Optional[str] = Query(
        default=None,
        description="配置分類過濾：basic/feature_flag/performance/security/business（可選）",
    ),
    current_user: User = Depends(require_system_admin),  # 僅 system_admin 可訪問
) -> JSONResponse:
    """
    獲取配置模板列表

    Args:
        category: 配置分類過濾（可選）
        current_user: 當前認證用戶

    Returns:
        配置模板列表
    """
    try:
        # 定義常用的配置模板
        templates = [
            {
                "name": "basic_database",
                "display_name": "基礎配置 - 數據庫連接",
                "category": "basic",
                "scope": "database.connection",
                "template": {
                    "host": "localhost",
                    "port": 8529,
                    "database": "ai_box",
                },
            },
            {
                "name": "feature_rag",
                "display_name": "功能開關 - RAG",
                "category": "feature_flag",
                "scope": "feature.rag",
                "template": {
                    "enabled": True,
                    "model": "gpt-4",
                    "chunk_size": 1000,
                },
            },
            {
                "name": "performance_timeout",
                "display_name": "性能參數 - 超時時間",
                "category": "performance",
                "scope": "performance.timeout",
                "template": {
                    "request_timeout": 30,
                    "retry_count": 3,
                    "retry_delay": 1,
                },
            },
            {
                "name": "security_encryption",
                "display_name": "安全參數 - 加密配置",
                "category": "security",
                "scope": "security.encryption",
                "template": {
                    "algorithm": "AES-256",
                    "key_rotation_days": 90,
                },
            },
        ]

        # 按分類過濾
        if category:
            templates = [t for t in templates if t["category"] == category]

        return APIResponse.success(
            data={"templates": templates, "total": len(templates)},
            message="Config templates retrieved successfully",
        )
    except Exception as e:
        logger.error(f"Failed to list config templates: {str(e)}", exc_info=True)
        return APIResponse.error(
            message=f"Failed to list config templates: {str(e)}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
