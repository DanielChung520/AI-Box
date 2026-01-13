# 代碼功能說明: 結果驗證器
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""結果驗證器 - 檢查結果完整性和有效性"""

import logging
from typing import Any, Dict, List, Optional

from ..models import ValidationResult

logger = logging.getLogger(__name__)


class ResultValidator:
    """結果驗證器"""

    def __init__(self) -> None:
        """初始化結果驗證器"""
        self._logger = logger

    def check_completeness(
        self,
        result: Dict[str, Any],
        required_fields: List[str],
        expected_count: Optional[int] = None,
    ) -> ValidationResult:
        """檢查結果完整性

        Args:
            result: 查詢結果
            required_fields: 必需字段列表
            expected_count: 預期結果數量（可選）

        Returns:
            驗證結果
        """
        issues: List[str] = []
        warnings: List[str] = []

        # 檢查必需字段
        for field in required_fields:
            if field not in result:
                issues.append(f"Missing required field: {field}")
            elif result[field] is None:
                warnings.append(f"Field {field} is None")

        # 檢查數據類型
        if "current_stock" in result:
            if not isinstance(result["current_stock"], int):
                issues.append("current_stock must be an integer")
            elif result["current_stock"] < 0:
                issues.append("current_stock cannot be negative")

        # 檢查結果行數
        row_count = result.get("row_count", 0)
        if row_count == 0:
            warnings.append("查詢返回 0 行數據")
        elif expected_count and row_count < expected_count:
            warnings.append(f"返回行數（{row_count}）少於預期（{expected_count}）")

        # 檢查執行時間
        execution_time = result.get("execution_time", 0)
        if execution_time > 10:
            warnings.append(f"查詢執行時間較長：{execution_time:.2f} 秒")

        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    def check_data_quality(
        self,
        rows: List[Dict[str, Any]],
        schema: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """檢查數據質量

        Args:
            rows: 數據行列表
            schema: Schema定義（可選）

        Returns:
            驗證結果
        """
        issues: List[str] = []
        warnings: List[str] = []

        if not rows:
            return ValidationResult(
                valid=False,
                issues=["沒有數據可檢查"],
                warnings=[],
            )

        # 檢查數據結構一致性
        if rows:
            first_row_keys = set(rows[0].keys())
            for i, row in enumerate(rows[1:], 1):
                row_keys = set(row.keys())
                if row_keys != first_row_keys:
                    warnings.append(
                        f"第 {i+1} 行數據結構不一致："
                        f"缺少字段 {first_row_keys - row_keys}, "
                        f"多餘字段 {row_keys - first_row_keys}"
                    )

        # 檢查空值
        for i, row in enumerate(rows):
            for key, value in row.items():
                if value is None:
                    warnings.append(f"第 {i+1} 行，字段 {key} 為空值")

        # 根據Schema驗證（如果提供）
        if schema:
            validation = self._validate_against_schema(rows, schema)
            issues.extend(validation.get("issues", []))
            warnings.extend(validation.get("warnings", []))

        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    def _validate_against_schema(
        self,
        rows: List[Dict[str, Any]],
        schema: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        """根據Schema驗證數據

        Args:
            rows: 數據行列表
            schema: Schema定義

        Returns:
            驗證結果（issues和warnings）
        """
        issues: List[str] = []
        warnings: List[str] = []

        json_schema = schema.get("json_schema", {})
        required_fields = json_schema.get("required", [])
        properties = json_schema.get("properties", {})

        for i, row in enumerate(rows):
            # 檢查必填字段
            for field in required_fields:
                if field not in row:
                    issues.append(f"第 {i+1} 行缺少必填字段: {field}")

            # 檢查字段類型
            for field, value in row.items():
                if field in properties:
                    expected_type = properties[field].get("type")
                    actual_type = self._get_python_type(value)

                    if expected_type and not self._type_matches(actual_type, expected_type):
                        warnings.append(
                            f"第 {i+1} 行，字段 {field} 類型不匹配：" f"期望 {expected_type}，實際 {actual_type}"
                        )

        return {"issues": issues, "warnings": warnings}

    def _get_python_type(self, value: Any) -> str:
        """獲取Python類型名稱

        Args:
            value: 值

        Returns:
            類型名稱
        """
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "number"
        elif isinstance(value, str):
            return "string"
        elif isinstance(value, list):
            return "array"
        elif isinstance(value, dict):
            return "object"
        else:
            return "unknown"

    def _type_matches(self, actual_type: str, expected_type: str) -> bool:
        """檢查類型是否匹配

        Args:
            actual_type: 實際類型
            expected_type: 期望類型

        Returns:
            是否匹配
        """
        type_mapping = {
            "boolean": "boolean",
            "integer": "integer",
            "number": "number",
            "string": "string",
            "array": "array",
            "object": "object",
        }

        return type_mapping.get(actual_type) == expected_type
