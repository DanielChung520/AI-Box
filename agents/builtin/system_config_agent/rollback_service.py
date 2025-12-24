# 代碼功能說明: Config Rollback Service - 配置回滾服務
# 創建日期: 2025-12-21
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-21

"""Config Rollback Service

配置回滾服務，基於審計日誌實現配置回滾功能（時光機功能）。
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

from services.api.core.log.log_service import LogService, get_log_service
from services.api.models.config import ConfigUpdate
from services.api.services.config_store_service import ConfigStoreService, get_config_store_service

from .models import RollbackResult

logger = logging.getLogger(__name__)


class ConfigRollbackService:
    """配置回滾服務 - 基於審計日誌實現回滾"""

    def __init__(self):
        """初始化配置回滾服務"""
        self._config_service: ConfigStoreService = get_config_store_service()
        self._log_service: LogService = get_log_service()
        self._logger = logger

    async def rollback_config(
        self,
        rollback_id: str,
        admin_user_id: str,
        scope: str,
        level: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> RollbackResult:
        """
        回滾配置到指定狀態

        Args:
            rollback_id: 審計日誌中的 rollback_id（或 trace_id）
            admin_user_id: 執行回滾的管理員 ID
            scope: 配置範圍
            level: 配置層級（system/tenant/user）
            tenant_id: 租戶 ID（用於查詢審計日誌）

        Returns:
            RollbackResult: 回滾結果
        """
        try:
            # 1. 從審計日誌中獲取變更記錄
            audit_log = await self._get_audit_log_by_rollback_id(
                rollback_id, scope, level, tenant_id
            )

            if not audit_log:
                return RollbackResult(
                    success=False,
                    message=f"Audit log not found for rollback_id: {rollback_id}",
                    rollback_id=rollback_id,
                    restored_config=None,
                )

            # 2. 提取變更前的配置
            content = audit_log.get("content", {})
            before_config = content.get("before") or content.get("before_config") or {}

            if not before_config:
                return RollbackResult(
                    success=False,
                    message="No previous configuration found in audit log",
                    rollback_id=rollback_id,
                    restored_config=None,
                )

            # 3. 確定配置 ID
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

            config_id = _generate_config_key(
                scope,
                tenant_id if level in ["tenant", "user"] else None,
                content.get("user_id") if level == "user" else None,
            )

            # 4. 執行回滾（更新配置為之前的狀態）
            config_update = ConfigUpdate(config_data=before_config)
            restored_config_model = self._config_service.update_config(
                config_id,
                config_update,
                tenant_id=tenant_id if level in ["tenant", "user"] else None,
                user_id=content.get("user_id") if level == "user" else None,
            )

            # 5. 生成新的 rollback_id（用於追蹤回滾操作）
            new_rollback_id = f"rb-{uuid.uuid4().hex[:8]}"

            # 6. 記錄回滾操作的審計日誌
            await self._log_service.log_audit(
                trace_id=new_rollback_id,
                actor=admin_user_id,
                action="rollback_config",
                content={
                    "original_rollback_id": rollback_id,
                    "scope": scope,
                    "level": level or "system",
                    "restored_config": before_config,
                    "restored_from_audit_log": audit_log.get("_key"),
                },
                level=level or "system",
                tenant_id=tenant_id,
                user_id=content.get("user_id"),
            )

            return RollbackResult(
                success=True,
                message=f"Config rolled back successfully to state before {rollback_id}",
                rollback_id=new_rollback_id,
                restored_config=restored_config_model.config_data,
            )

        except Exception as e:
            self._logger.error(f"Rollback failed: {e}", exc_info=True)
            return RollbackResult(
                success=False,
                message=f"Rollback failed: {str(e)}",
                rollback_id=rollback_id,
                restored_config=None,
            )

    async def get_recent_changes(
        self,
        scope: Optional[str] = None,
        level: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 10,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """
        獲取最近的配置變更（用於回滾選擇）

        Args:
            scope: 配置範圍（可選，用於過濾）
            level: 配置層級（可選，用於過濾）
            tenant_id: 租戶 ID（可選，用於過濾）
            limit: 返回的最大記錄數
            hours: 查詢最近多少小時的變更

        Returns:
            最近的配置變更列表
        """
        try:
            # TODO: 實現實際的審計日誌查詢
            # 這需要 LogService 提供查詢接口
            # 查詢條件應該包括：
            # - log_type: "audit"
            # - agent_name: "SystemConfigAgent"
            # - action: ["update_config", "create_config", "delete_config"]
            # - scope, level, tenant_id 等過濾條件
            # - 時間範圍過濾（最近 hours 小時）
            if scope:
                # 注意：這裡需要根據 LogService 的實際查詢接口調整
                # 簡化實現：返回空列表，實際應該調用 LogService 的查詢方法
                pass

            # TODO: 實現實際的審計日誌查詢
            # 這需要 LogService 提供查詢接口
            # 目前返回空列表，表示功能待實現
            self._logger.warning(
                "get_recent_changes: LogService query interface not yet implemented"
            )
            return []

        except Exception as e:
            self._logger.error(f"Failed to get recent changes: {e}", exc_info=True)
            return []

    async def _get_audit_log_by_rollback_id(
        self,
        rollback_id: str,
        scope: str,
        level: Optional[str],
        tenant_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """
        從審計日誌中獲取指定 rollback_id 的記錄

        Args:
            rollback_id: rollback_id 或 trace_id
            scope: 配置範圍
            level: 配置層級
            tenant_id: 租戶 ID

        Returns:
            審計日誌記錄（如果找到）
        """
        try:
            # TODO: 實現實際的審計日誌查詢
            # 這需要 LogService 提供查詢接口來根據 rollback_id 或 trace_id 查詢
            # 目前返回 None，表示功能待實現
            # 實際實現應該類似：
            # audit_logs = await self._log_service.query_audit_logs(
            #     trace_id=rollback_id,
            #     action="update_config",
            #     scope=scope,
            #     limit=1
            # )
            # return audit_logs[0] if audit_logs else None

            self._logger.warning(
                f"_get_audit_log_by_rollback_id: LogService query interface not yet implemented for rollback_id: {rollback_id}"
            )
            return None

        except Exception as e:
            self._logger.error(f"Failed to get audit log: {e}", exc_info=True)
            return None
