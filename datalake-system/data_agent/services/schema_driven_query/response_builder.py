# -*- coding: utf-8 -*-
"""
結構化回應建構器

職責：
- 將查詢結果轉換為結構化 JSON 格式
- 包含 SQL、數據、執行時間等資訊
- 處理錯誤回應

使用方式：
    builder = ResponseBuilder()

    # 成功回應
    response = builder.build_success(
        sql="SELECT ...",
        data=[...],
        row_count=10,
        execution_time_ms=150.5
    )

    # 錯誤回應
    response = builder.build_error(
        error_code="SCHEMA_NOT_FOUND",
        message="找不到指定的表格",
        details="Table 'unknown' does not exist"
    )
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import time


class ResponseStatus(Enum):
    """回應狀態」"""

    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"  # 部分成功（有警告）


class ErrorCode(Enum):
    """Data-Agent 錯誤碼」"""

    # 預驗證錯誤（由 PreValidator 產生）
    SCHEMA_NOT_FOUND = "SCHEMA_NOT_FOUND"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    QUERY_SCOPE_TOO_LARGE = "QUERY_SCOPE_TOO_LARGE"
    MISSING_REQUIRED_PARAM = "MISSING_REQUIRED_PARAM"
    INVALID_PARAM_FORMAT = "INVALID_PARAM_FORMAT"

    # 執行時錯誤
    NO_DATA_FOUND = "NO_DATA_FOUND"
    SCHEMA_ERROR = "SCHEMA_ERROR"
    CONNECTION_TIMEOUT = "CONNECTION_TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"

    # SQL 生成錯誤
    SQL_GENERATION_FAILED = "SQL_GENERATION_FAILED"
    SQL_VALIDATION_FAILED = "SQL_VALIDATION_FAILED"


@dataclass
class ErrorDetail:
    """錯誤詳情」"""

    code: str
    message: str
    column_name: Optional[str] = None
    value: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)
    exception: Optional[str] = None


@dataclass
class QueryResult:
    """查詢結果"""

    sql: str
    data: List[Dict[str, Any]] = field(default_factory=list)
    row_count: int = 0
    columns: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    schema_used: Optional[str] = None
    pagination: Optional[Dict[str, Any]] = None
    token_usage: Optional[Dict[str, int]] = None


@dataclass
class StructuredResponse:
    """結構化回應」"""

    status: str  # "success" | "error" | "partial"
    task_id: str
    result: Optional[QueryResult] = None
    errors: List[ErrorDetail] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # 向後兼容欄位
    error_code: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典（移除 None 值）」"""
        return {k: v for k, v in asdict(self).items() if v is not None}


class ResponseBuilder:
    """結構化回應建構器」"""

    def __init__(self, task_id: str):
        """
        初始化

        Args:
            task_id: 任務 ID
        """
        self.task_id = task_id
        self._start_time: Optional[float] = None

    def start_timing(self):
        """開始計時」"""
        self._start_time = time.time()

    def stop_timing(self) -> float:
        """停止計時並返回經過的毫秒數」"""
        if self._start_time is None:
            return 0.0
        return (time.time() - self._start_time) * 1000

    def build_success(
        self,
        sql: str,
        data: List[Dict[str, Any]],
        columns: Optional[List[str]] = None,
        schema_used: Optional[str] = None,
        pagination: Optional[Dict[str, Any]] = None,
        token_usage: Optional[Dict[str, int]] = None,
    ) -> StructuredResponse:
        """
        建立成功回應

        Args:
            sql: 生成的 SQL 查詢
            data: 查詢結果數據
            columns: 欄位名稱列表
            schema_used: 使用的 schema 名稱
            pagination: 分頁資訊
            token_usage: Token 使用量

        Returns:
            StructuredResponse: 結構化成功回應
        """
        execution_time = self.stop_timing()

        result = QueryResult(
            sql=sql,
            data=data,
            row_count=len(data),
            columns=columns or self._extract_columns(data),
            execution_time_ms=round(execution_time, 2),
            schema_used=schema_used,
            pagination=pagination,
            token_usage=token_usage,
        )

        return StructuredResponse(
            status=ResponseStatus.SUCCESS.value,
            task_id=self.task_id,
            result=result,
            error_code=None,
            message=None,
            metadata={"timestamp": time.time()},
        )

    def build_error(
        self,
        error_code: str,
        message: str,
        column_name: Optional[str] = None,
        value: Optional[str] = None,
        suggestions: Optional[List[str]] = None,
        exception: Optional[str] = None,
        sql: Optional[str] = None,
    ) -> StructuredResponse:
        """
        建立錯誤回應

        Args:
            error_code: 錯誤碼
            message: 錯誤訊息
            column_name: 錯誤欄位名稱
            value: 錯誤值
            suggestions: 建議列表
            exception: 例外詳情
            sql: 相關的 SQL（如果有）

        Returns:
            StructuredResponse: 結構化錯誤回應
        """
        error_detail = ErrorDetail(
            code=error_code,
            message=message,
            column_name=column_name,
            value=value,
            suggestions=suggestions or [],
            exception=exception,
        )

        # 如果有 SQL，添加到 result 中
        result: Optional[QueryResult] = None
        if sql:
            result = QueryResult(sql=sql, data=[], row_count=0)

        return StructuredResponse(
            status=ResponseStatus.ERROR.value,
            task_id=self.task_id,
            result=result,
            errors=[error_detail],
            error_code=error_code,
            message=message,
            metadata={"timestamp": time.time()},
        )

    def build_partial(
        self,
        sql: str,
        data: List[Dict[str, Any]],
        warnings: List[str],
        columns: Optional[List[str]] = None,
        schema_used: Optional[str] = None,
    ) -> StructuredResponse:
        """
        建立部分成功回應（有警告）

        Args:
            sql: 生成的 SQL 查詢
            data: 查詢結果數據
            warnings: 警告列表
            columns: 欄位名稱列表
            schema_used: 使用的 schema 名稱

        Returns:
            StructuredResponse: 結構化部分成功回應
        """
        execution_time = self.stop_timing()

        result = QueryResult(
            sql=sql,
            data=data,
            row_count=len(data),
            columns=columns or self._extract_columns(data),
            execution_time_ms=round(execution_time, 2),
            schema_used=schema_used,
        )

        return StructuredResponse(
            status=ResponseStatus.PARTIAL.value,
            task_id=self.task_id,
            result=result,
            warnings=warnings,
            error_code=None,
            message=None,
            metadata={"timestamp": time.time()},
        )

    def validate_and_build_response(
        self,
        sql: str,
        data: List[Dict[str, Any]],
        params: Optional[Dict[str, Any]] = None,
        schema_used: Optional[str] = None,
    ) -> StructuredResponse:
        """
        後置檢查：數據驗證 + 空結果確認

        1. 數據驗證：簡單目標比對（如料號是否在結果中）
        2. 空結果確認：區分"正常無數據"和"查詢問題"

        Args:
            sql: 執行的 SQL
            data: 查詢結果
            params: 查詢參數（用於驗證）
            schema_used: 使用的 schema

        Returns:
            StructuredResponse: 成功或部分成功回應
        """
        warnings = []
        execution_time = self.stop_timing()

        # 1. 空結果檢查
        if not data or len(data) == 0:
            # 嘗試判斷是"正常無數據"還是"查詢問題"
            if params:
                # 有參數但沒結果，可能是參數不存在
                missing_info = []
                if params.get("material_id"):
                    missing_info.append(f"料號 '{params['material_id']}' 不存在或無庫存")
                if params.get("inventory_location"):
                    missing_info.append(f"倉庫 '{params['inventory_location']}' 不存在或無庫存")

                if missing_info:
                    message = "查詢不到數據：" + "；".join(missing_info)
                    warnings.append("NO_DATA_BUT_PARAMS_EXIST")
                else:
                    message = "查詢不到任何符合的數據"
            else:
                message = "查詢不到任何符合的數據"

            result = QueryResult(
                sql=sql,
                data=[],
                row_count=0,
                columns=[],
                execution_time_ms=round(execution_time, 2),
                schema_used=schema_used,
            )

            # 如果有參數但沒結果，視為 PARTIAL（可能是參數問題）
            if params and any(params.values()):
                return StructuredResponse(
                    status=ResponseStatus.PARTIAL.value,
                    task_id=self.task_id,
                    result=result,
                    warnings=["查不到數據，但 SQL 執行成功，可能是參數不存在"],
                    error_code=ErrorCode.NO_DATA_FOUND.value,
                    message=message,
                    metadata={"timestamp": time.time()},
                )

            return StructuredResponse(
                status=ResponseStatus.ERROR.value,
                task_id=self.task_id,
                result=result,
                error_code=ErrorCode.NO_DATA_FOUND.value,
                message=message,
                metadata={"timestamp": time.time()},
            )

        # 2. 數據驗證：檢查關鍵字段是否存在
        columns = list(data[0].keys()) if data else []
        validated_data = data

        # 3. 如果有 params，檢查關鍵字段是否有值
        if params and params.get("material_id"):
            expected_item = params["material_id"]
            items_in_result = {str(row.get("item_no", "")).strip() for row in data}
            if expected_item not in items_in_result:
                warnings.append(f"輸入的料號 '{expected_item}' 不在查詢結果中")

        # 4. 構建成功回應
        result = QueryResult(
            sql=sql,
            data=validated_data,
            row_count=len(validated_data),
            columns=columns,
            execution_time_ms=round(execution_time, 2),
            schema_used=schema_used,
        )

        # 如果有警告，返回 PARTIAL
        if warnings:
            return StructuredResponse(
                status=ResponseStatus.PARTIAL.value,
                task_id=self.task_id,
                result=result,
                warnings=warnings,
                error_code=None,
                message=None,
                metadata={"timestamp": time.time()},
            )

        return StructuredResponse(
            status=ResponseStatus.SUCCESS.value,
            task_id=self.task_id,
            result=result,
            error_code=None,
            message=None,
            metadata={"timestamp": time.time()},
        )

    def add_warning(self, warning: str) -> List[str]:
        """添加警告（用於鏈式調用）」"""
        # 這個方法需要在創建 response 後調用
        # 實際使用時建議直接構造
        return [warning]

    def merge_errors(self, errors: List[ErrorDetail]) -> StructuredResponse:
        """
        合併多個錯誤

        Args:
            errors: 錯誤詳情列表

        Returns:
            StructuredResponse: 包含多個錯誤的回應
        """
        return StructuredResponse(
            status=ResponseStatus.ERROR.value,
            task_id=self.task_id,
            errors=errors,
            error_code="MULTIPLE_ERRORS",
            message=f"Found {len(errors)} validation errors",
            metadata={"timestamp": time.time()},
        )

    @staticmethod
    def _extract_columns(data: List[Dict[str, Any]]) -> List[str]:
        """從數據中提取欄位名稱」"""
        if not data:
            return []
        return list(data[0].keys())

    @staticmethod
    def from_prevalidator_result(
        task_id: str, validation_result, sql: Optional[str] = None
    ) -> StructuredResponse:
        """
        從 PreValidator 的 ValidationResult 轉換為 StructuredResponse

        Args:
            task_id: 任務 ID
            validation_result: PreValidator.validate() 的回傳值
            sql: 相關的 SQL（如果有）

        Returns:
            StructuredResponse: 結構化回應
        """
        if validation_result.valid:
            return StructuredResponse(
                status=ResponseStatus.SUCCESS.value,
                task_id=task_id,
                error_code=None,
                message=None,
                metadata={"timestamp": time.time()},
            )

        errors = [
            ErrorDetail(
                code=getattr(ErrorCode, e.code, ErrorCode.INTERNAL_ERROR).value
                if hasattr(ErrorCode, e.code)
                else e.code,
                message=e.message,
                column_name=e.column_name,
                value=e.value,
                suggestions=e.suggestions,
            )
            for e in validation_result.errors
        ]

        result = QueryResult(sql=sql) if sql else None

        # 提取主要錯誤碼和訊息
        main_error_code = errors[0].code if errors else "INTERNAL_ERROR"
        main_error_message = errors[0].message if errors else "Unknown error"

        return StructuredResponse(
            status=ResponseStatus.ERROR.value,
            task_id=task_id,
            result=result,
            errors=errors,
            warnings=validation_result.warnings,
            error_code=main_error_code,
            message=main_error_message,
            metadata={"timestamp": time.time()},
        )


async def demo():
    """演示」"""
    import uuid

    # Demo 1: 成功回應
    print("=== Demo 1: 成功回應 ===")
    task_id = str(uuid.uuid4())
    builder = ResponseBuilder(task_id)
    builder.start_timing()

    response = builder.build_success(
        sql="SELECT ma025, ma017 FROM ma WHERE ma001 = '10-0001'",
        data=[{"ma025": "產品名稱", "ma017": "規格說明"}],
        columns=["ma025", "ma017"],
        schema_used="mart_item",
    )

    import json

    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))

    # Demo 2: 錯誤回應
    print("\n=== Demo 2: 錯誤回應 ===")
    task_id = str(uuid.uuid4())
    builder = ResponseBuilder(task_id)

    response = builder.build_error(
        error_code="SCHEMA_NOT_FOUND",
        message="找不到指定的表格",
        column_name="table_name",
        value="unknown_table",
        suggestions=["請檢查表格名稱是否正確", "可用的表格：mart_item, mart_inventory"],
    )

    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))

    # Demo 3: 部分成功回應
    print("\n=== Demo 3: 部分成功回應 ===")
    task_id = str(uuid.uuid4())
    builder = ResponseBuilder(task_id)
    builder.start_timing()

    response = builder.build_partial(
        sql="SELECT * FROM mart_inventory LIMIT 1000",
        data=[{"col1": "val1"}, {"col1": "val2"}],
        warnings=["查詢結果已限制為 1000 行"],
        columns=["col1"],
        schema_used="mart_inventory",
    )

    print(json.dumps(response.to_dict(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
