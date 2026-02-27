# 代碼功能說明: 數據驗證器
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""數據驗證器 - 庫存狀態判斷和數據一致性檢查"""

import logging
from typing import Any, Dict

from ..models import StockStatus, ValidationResult

logger = logging.getLogger(__name__)


class DataValidator:
    """數據驗證器"""

    def __init__(self) -> None:
        """初始化數據驗證器"""
        self._logger = logger

    def analyze_stock_status(
        self,
        current_stock: int,
        safety_stock: int,
    ) -> StockStatus:
        """分析庫存狀態

        Args:
            current_stock: 當前庫存
            safety_stock: 安全庫存

        Returns:
            庫存狀態
        """
        if current_stock >= safety_stock:
            status = "normal"
            shortage_quantity = 0
        elif current_stock >= safety_stock * 0.5:
            status = "low"
            shortage_quantity = safety_stock - current_stock
        else:
            status = "shortage"
            shortage_quantity = safety_stock - current_stock

        return StockStatus(
            status=status,
            current_stock=current_stock,
            safety_stock=safety_stock,
            shortage_quantity=shortage_quantity,
            is_shortage=(status == "shortage"),
        )

    def validate_data(
        self,
        part_info: Dict[str, Any],
        stock_info: Dict[str, Any],
    ) -> ValidationResult:
        """驗證數據有效性

        Args:
            part_info: 物料信息
            stock_info: 庫存信息

        Returns:
            驗證結果
        """
        issues: list[str] = []
        warnings: list[str] = []

        # 檢查料號一致性
        part_number_part = part_info.get("part_number")
        part_number_stock = stock_info.get("part_number")
        if part_number_part and part_number_stock:
            if part_number_part != part_number_stock:
                issues.append(f"Part number mismatch: {part_number_part} vs {part_number_stock}")

        # 檢查安全庫存
        safety_stock = part_info.get("safety_stock")
        if safety_stock is None:
            warnings.append("safety_stock is not defined in part info")
        elif safety_stock <= 0:
            issues.append("safety_stock must be greater than 0")

        # 檢查當前庫存 - 支援多個欄位名稱
        current_stock = stock_info.get("current_stock") or stock_info.get("img10")
        if current_stock is None:
            issues.append("current_stock is missing in stock info")
        elif current_stock < 0:
            issues.append("current_stock cannot be negative")

        return ValidationResult(
            valid=len(issues) == 0,
            issues=issues,
            warnings=warnings,
        )

    def handle_data_anomalies(
        self,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """處理數據異常情況

        Args:
            result: 查詢結果

        Returns:
            添加了異常信息的結果
        """
        anomalies: list[str] = []

        # 檢查異常值
        if "current_stock" in result:
            current_stock = result["current_stock"]
            if current_stock == 0:
                anomalies.append("庫存為零，需要立即補貨")
            elif current_stock < 0:
                anomalies.append("庫存為負數，數據異常")

        # 檢查時間戳
        if "last_updated" in result:
            from datetime import datetime

            try:
                last_updated = datetime.fromisoformat(result["last_updated"])
                days_since_update = (datetime.now() - last_updated).days
                if days_since_update > 30:
                    anomalies.append(f"庫存數據已 {days_since_update} 天未更新")
            except (ValueError, TypeError):
                warnings = result.get("warnings", [])
                warnings.append("無法解析 last_updated 時間戳")
                result["warnings"] = warnings

        result["anomalies"] = anomalies
        result["has_anomalies"] = len(anomalies) > 0

        return result
