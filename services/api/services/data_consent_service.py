# 代碼功能說明: 數據使用同意服務
# 創建日期: 2025-12-06
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-06

"""數據使用同意服務 - 管理用戶數據使用同意記錄。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, List, Dict, Any
import structlog

from database.arangodb import ArangoDBClient, ArangoCollection
from services.api.models.data_consent import (
    DataConsent,
    DataConsentCreate,
    ConsentType,
)

logger = structlog.get_logger(__name__)

# ArangoDB 集合名稱
CONSENT_COLLECTION_NAME = "data_consents"


class DataConsentService:
    """數據使用同意服務類"""

    def __init__(self, client: Optional[ArangoDBClient] = None):
        """初始化數據使用同意服務。

        Args:
            client: ArangoDB 客戶端，如果不提供則創建新實例
        """
        self.client = client or ArangoDBClient()

        # 確保集合存在
        if self.client.db is not None:
            if not self.client.db.has_collection(CONSENT_COLLECTION_NAME):
                self.client.db.create_collection(CONSENT_COLLECTION_NAME)
                logger.info("Created collection", collection=CONSENT_COLLECTION_NAME)
        else:
            raise RuntimeError("ArangoDB client is not connected")

        # 獲取集合
        collection = self.client.db.collection(CONSENT_COLLECTION_NAME)
        self.collection = ArangoCollection(collection)

    def record_consent(
        self,
        user_id: str,
        consent_create: DataConsentCreate,
    ) -> DataConsent:
        """記錄用戶同意狀態。

        Args:
            user_id: 用戶ID
            consent_create: 同意創建請求

        Returns:
            創建的同意記錄
        """
        # 檢查是否已存在相同類型的同意記錄
        existing = self._get_consent_by_type(user_id, consent_create.consent_type)

        consent_data = {
            "user_id": user_id,
            "consent_type": consent_create.consent_type.value,
            "purpose": consent_create.purpose,
            "granted": consent_create.granted,
            "timestamp": datetime.utcnow().isoformat(),
            "expires_at": (
                consent_create.expires_at.isoformat()
                if consent_create.expires_at
                else None
            ),
        }

        if existing:
            # 更新現有記錄
            consent_data["_key"] = existing["_key"]
            result = self.collection.update(consent_data)
            logger.info(
                "Updated consent record",
                user_id=user_id,
                consent_type=consent_create.consent_type.value,
                granted=consent_create.granted,
            )
            updated = result.get("new") or consent_data
            return self._document_to_consent(updated)
        else:
            # 創建新記錄
            # 使用 user_id 和 consent_type 生成唯一 key
            key = f"{user_id}_{consent_create.consent_type.value}"
            consent_data["_key"] = key
            result = self.collection.insert(consent_data)
            logger.info(
                "Created consent record",
                user_id=user_id,
                consent_type=consent_create.consent_type.value,
                granted=consent_create.granted,
            )
            created = result.get("new") or consent_data
            return self._document_to_consent(created)

    def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """檢查用戶是否已同意特定類型。

        Args:
            user_id: 用戶ID
            consent_type: 同意類型

        Returns:
            如果用戶已同意且未過期則返回 True
        """
        consent = self._get_consent_by_type(user_id, consent_type)
        if not consent:
            return False

        # 檢查是否已同意
        if not consent.get("granted", False):
            return False

        # 檢查是否過期
        expires_at = consent.get("expires_at")
        if expires_at:
            try:
                if isinstance(expires_at, str):
                    expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                else:
                    expires = expires_at
                if expires < datetime.utcnow():
                    return False
            except Exception as e:
                logger.warning("Failed to parse expires_at", error=str(e))

        return True

    def revoke_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """撤銷用戶同意。

        Args:
            user_id: 用戶ID
            consent_type: 同意類型

        Returns:
            是否成功撤銷
        """
        consent = self._get_consent_by_type(user_id, consent_type)
        if not consent:
            return False

        # 更新為未同意
        key = consent["_key"]
        update_data = {
            "_key": key,
            "granted": False,
            "timestamp": datetime.utcnow().isoformat(),
        }

        self.collection.update(update_data)
        logger.info(
            "Revoked consent",
            user_id=user_id,
            consent_type=consent_type.value,
        )
        return True

    def get_user_consents(
        self,
        user_id: str,
    ) -> List[DataConsent]:
        """查詢用戶的所有同意記錄。

        Args:
            user_id: 用戶ID

        Returns:
            用戶的所有同意記錄列表
        """
        if self.client.db is None:
            raise RuntimeError("ArangoDB client is not connected")

        # 查詢用戶的所有同意記錄
        query = """
        FOR consent IN @@collection
            FILTER consent.user_id == @user_id
            SORT consent.timestamp DESC
            RETURN consent
        """

        bind_vars = {
            "@collection": CONSENT_COLLECTION_NAME,
            "user_id": user_id,
        }

        cursor = self.client.db.aql.execute(query, bind_vars=bind_vars)
        results = [doc for doc in cursor]

        return [self._document_to_consent(doc) for doc in results]

    def _get_consent_by_type(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> Optional[Dict[str, Any]]:
        """根據用戶ID和同意類型獲取同意記錄。

        Args:
            user_id: 用戶ID
            consent_type: 同意類型

        Returns:
            同意記錄文檔，如果不存在則返回 None
        """
        key = f"{user_id}_{consent_type.value}"
        try:
            return self.collection.get(key)
        except Exception:
            return None

    @staticmethod
    def _document_to_consent(doc: Dict[str, Any]) -> DataConsent:
        """將 ArangoDB 文檔轉換為 DataConsent 對象。

        Args:
            doc: ArangoDB 文檔

        Returns:
            DataConsent 對象
        """
        # 處理時間字段
        timestamp = doc.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.utcnow()

        expires_at = doc.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        elif expires_at == "":
            expires_at = None

        return DataConsent(
            user_id=doc["user_id"],
            consent_type=ConsentType(doc["consent_type"]),
            purpose=doc["purpose"],
            granted=doc["granted"],
            timestamp=timestamp,
            expires_at=expires_at,
        )


# 全局服務實例（單例模式）
_consent_service: Optional[DataConsentService] = None


def get_consent_service() -> DataConsentService:
    """獲取數據使用同意服務實例（單例模式）。

    Returns:
        DataConsentService 實例
    """
    global _consent_service

    if _consent_service is None:
        _consent_service = DataConsentService()

    return _consent_service
