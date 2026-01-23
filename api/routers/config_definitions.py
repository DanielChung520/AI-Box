# 代碼功能說明: Config Definitions API 路由
# 創建日期: 2026-01-20
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-20

"""Config Definitions API

提供配置定義的查詢和驗證功能：
- GET /api/v1/config/definitions - 列出所有配置定義
- GET /api/v1/config/definitions/{scope} - 取得特定配置定義
- POST /api/v1/config/definitions/{scope}/validate - 驗證配置是否符合定義
"""

from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from services.api.core.config import get_definition_loader

router = APIRouter(prefix="/config/definitions", tags=["Config Definitions"])


class ConfigDefinitionResponse(BaseModel):
    """配置定義響應"""

    scope: str = Field(..., description="配置範圍")
    description: str = Field(..., description="配置描述")
    version: str = Field(..., description="版本號")
    fields: Dict[str, Any] = Field(..., description="字段定義")
    convergence_rules: Dict[str, Any] = Field(default_factory=dict, description="收斂規則")
    last_updated: str = Field(..., description="最後更新時間")


class ConfigValidationRequest(BaseModel):
    """配置驗證請求"""

    config_data: Dict[str, Any] = Field(..., description="要驗證的配置數據")


class ConfigValidationResponse(BaseModel):
    """配置驗證響應"""

    valid: bool = Field(..., description="是否有效")
    scope: str = Field(..., description="配置範圍")
    errors: List[str] = Field(default_factory=list, description="錯誤列表")
    warnings: List[str] = Field(default_factory=list, description="警告列表")


class ConfigDefinitionsListResponse(BaseModel):
    """配置定義列表響應"""

    definitions: List[str] = Field(..., description="配置定義範圍列表")
    count: int = Field(..., description="數量")


@router.get("", response_model=ConfigDefinitionsListResponse)
async def list_config_definitions() -> ConfigDefinitionsListResponse:
    """
    列出所有配置定義

    Returns:
        ConfigDefinitionsListResponse: 配置定義列表
    """
    loader = get_definition_loader()
    if loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config definition loader is not available",
        )

    definitions = loader._cache
    return ConfigDefinitionsListResponse(
        definitions=list(definitions.keys()),
        count=len(definitions),
    )


@router.get("/{scope}", response_model=ConfigDefinitionResponse)
async def get_config_definition(scope: str) -> ConfigDefinitionResponse:
    """
    取得特定配置定義

    Args:
        scope: 配置範圍

    Returns:
        ConfigDefinitionResponse: 配置定義
    """
    loader = get_definition_loader()
    if loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config definition loader is not available",
        )

    definition = loader.get_definition(scope)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config definition not found for scope: {scope}",
        )

    return ConfigDefinitionResponse(
        scope=definition.get("scope", scope),
        description=definition.get("description", ""),
        version=definition.get("version", "1.0.0"),
        fields=definition.get("fields", {}),
        convergence_rules=definition.get("convergence_rules", {}),
        last_updated=definition.get("last_updated", ""),
    )


@router.post("/{scope}/validate", response_model=ConfigValidationResponse)
async def validate_config(
    scope: str,
    request: ConfigValidationRequest,
) -> ConfigValidationResponse:
    """
    驗證配置是否符合定義

    Args:
        scope: 配置範圍
        request: 驗證請求

    Returns:
        ConfigValidationResponse: 驗證結果
    """
    loader = get_definition_loader()
    if loader is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Config definition loader is not available",
        )

    definition = loader.get_definition(scope)
    if definition is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Config definition not found for scope: {scope}",
        )

    errors = []
    warnings = []
    fields = definition.get("fields", {})
    config_data = request.config_data

    for field_name, field_value in config_data.items():
        if field_name not in fields:
            errors.append(f"Unknown field: {field_name}")
            continue

        field_def = fields[field_name]

        # 類型檢查
        expected_type = field_def.get("type")
        if expected_type:
            type_valid = _check_type(field_value, expected_type)
            if not type_valid:
                errors.append(
                    f"Field '{field_name}': expected type {expected_type}, "
                    f"got {type(field_value).__name__}"
                )

        # 數值邊界檢查
        if expected_type in ("integer", "number"):
            if "min" in field_def and field_value < field_def["min"]:
                errors.append(
                    f"Field '{field_name}': value {field_value} is less than minimum {field_def['min']}"
                )
            if "max" in field_def and field_value > field_def["max"]:
                errors.append(
                    f"Field '{field_name}': value {field_value} exceeds maximum {field_def['max']}"
                )

        # 枚舉值檢查
        if "options" in field_def:
            options = field_def["options"]
            if isinstance(field_value, list):
                invalid_values = [v for v in field_value if v not in options]
                if invalid_values:
                    errors.append(
                        f"Field '{field_name}': contains invalid values {invalid_values}. "
                        f"Allowed values: {options}"
                    )
            else:
                if field_value not in options:
                    errors.append(
                        f"Field '{field_name}': value '{field_value}' is not in allowed list. "
                        f"Allowed values: {options}"
                    )

    valid = len(errors) == 0
    return ConfigValidationResponse(
        valid=valid,
        scope=scope,
        errors=errors,
        warnings=warnings,
    )


def _check_type(value: Any, expected_type: str) -> bool:
    """檢查類型是否匹配"""
    type_map = {
        "integer": int,
        "number": (int, float),
        "string": str,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    expected = type_map.get(expected_type)
    if expected is None:
        return True

    if isinstance(expected, tuple):
        return isinstance(value, expected)
    return isinstance(value, expected)
