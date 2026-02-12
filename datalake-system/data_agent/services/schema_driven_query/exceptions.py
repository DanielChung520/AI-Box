# -*- coding: utf-8 -*-
"""
Data-Agent-JP 自定義異常類別

建立日期: 2026-02-10
建立人: Daniel Chung
最後修改日期: 2026-02-10
"""

from typing import Dict, Optional, Any, List


class DataAgentJPError(Exception):
    """Data-Agent-JP 基礎異常類別"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details if details is not None else {}


class ValidationError(DataAgentJPError):
    """當 Entity Validation 失敗時拋出"""

    def __init__(
        self,
        message: str = "",
        entity_type: Optional[str] = None,
        entity_value: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        msg = message or ""
        if not msg and entity_type and entity_value:
            msg = f"{entity_type} '{entity_value}' 不存在於 Master Data 中"
        elif not msg:
            msg = "Entity 驗證失敗"

        err_details: Dict[str, Any] = {}
        if details is not None:
            err_details.update(details)
        if entity_type is not None:
            err_details["entity_type"] = entity_type
        if entity_value is not None:
            err_details["entity_value"] = entity_value
        if suggestions is not None:
            err_details["suggestions"] = suggestions

        super().__init__(msg, err_details if err_details else None)
        self.entity_type = entity_type
        self.entity_value = entity_value
        self.suggestions = suggestions if suggestions is not None else []


class ItemNotFoundError(ValidationError):
    """料號不存在於 Master Data"""

    def __init__(self, item_no: str, suggestions: Optional[List[str]] = None):
        msg = f"料號 '{item_no}' 不存在於 Master Data 中"
        super().__init__(msg, entity_type="item", entity_value=item_no, suggestions=suggestions)


class WarehouseNotFoundError(ValidationError):
    """倉庫代碼不存在於 Master Data"""

    def __init__(self, warehouse_no: str, suggestions: Optional[List[str]] = None):
        msg = f"倉庫代碼 '{warehouse_no}' 不存在於 Master Data 中"
        super().__init__(
            msg, entity_type="warehouse", entity_value=warehouse_no, suggestions=suggestions
        )


class WorkstationNotFoundError(ValidationError):
    """工作站 ID 不存在於 Master Data"""

    def __init__(self, workstation_id: str, suggestions: Optional[List[str]] = None):
        msg = f"工作站 ID '{workstation_id}' 不存在於 Master Data 中"
        super().__init__(
            msg, entity_type="workstation", entity_value=workstation_id, suggestions=suggestions
        )


class MasterDataLoadError(DataAgentJPError):
    """載入 Master Data 失敗"""

    def __init__(self, file_path: str, reason: Optional[str] = None):
        msg = f"載入 Master Data 失敗: {file_path}"
        details: Dict[str, Any] = {"file_path": file_path}
        if reason is not None:
            details["reason"] = reason
        super().__init__(msg, details)


class IntentParseError(DataAgentJPError):
    """NLQ 解析失敗"""

    def __init__(self, nlq: str, reason: Optional[str] = None):
        msg = f"無法解析自然語言查詢"
        details: Dict[str, Any] = {"nlq": nlq}
        if reason is not None:
            details["reason"] = reason
        super().__init__(msg, details)


class SQLGenerationError(DataAgentJPError):
    """SQL 生成失敗"""

    def __init__(
        self, reason: str, intent: Optional[str] = None, bindings: Optional[Dict[str, Any]] = None
    ):
        msg = f"SQL 生成失敗: {reason}"
        details: Dict[str, Any] = {}
        if intent is not None:
            details["intent"] = intent
        if bindings is not None:
            details["bindings"] = bindings
        super().__init__(msg, details)


class DatabaseConnectionError(DataAgentJPError):
    """資料庫連線失敗"""

    def __init__(self, database: str, reason: Optional[str] = None):
        msg = f"資料庫連線失敗: {database}"
        details: Dict[str, Any] = {"database": database}
        if reason is not None:
            details["reason"] = reason
        super().__init__(msg, details)


class QueryTimeoutError(DataAgentJPError):
    """查詢超時"""

    def __init__(self, timeout: int, query: Optional[str] = None):
        msg = f"查詢超時 (timeout={timeout}s)"
        details: Dict[str, Any] = {"timeout": timeout}
        if query is not None:
            details["query"] = query
        super().__init__(msg, details)


class TokenLimitExceededError(DataAgentJPError):
    """Token 數量超過限制"""

    def __init__(self, prompt_tokens: int, completion_tokens: int, limit: int):
        msg = f"Token 數量超過限制: {prompt_tokens + completion_tokens} > {limit}"
        details: Dict[str, Any] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "limit": limit,
        }
        super().__init__(msg, details)
