# -*- coding: utf-8 -*-
"""
查詢前驗證器

職責：
- 在執行查詢前，檢查是否存在問題
- 返回結構化錯誤資訊

使用方式：
    validator = PreValidator()
    result = await validator.validate(query, intent, entities)

    if not result.valid:
        # 有錯誤，檢查 result.errors
        for error in result.errors:
            print(f'{error.code}: {error.message}')
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ErrorCode(Enum):
    """錯誤碼」"""

    SCHEMA_NOT_FOUND = "SCHEMA_NOT_FOUND"
    INTENT_UNCLEAR = "INTENT_UNCLEAR"
    UNAUTHORIZED_ACCESS = "UNAUTHORIZED_ACCESS"
    QUERY_SCOPE_TOO_LARGE = "QUERY_SCOPE_TOO_LARGE"
    MISSING_REQUIRED_PARAM = "MISSING_REQUIRED_PARAM"
    INVALID_PARAM_FORMAT = "INVALID_PARAM_FORMAT"


@dataclass
class ValidationError:
    """驗證錯誤」"""

    code: str  # 錯誤碼
    message: str  # 錯誤訊息
    column_name: Optional[str] = None  # 錯誤欄位名稱
    value: Optional[str] = None  # 錯誤值
    suggestions: List[str] = field(default_factory=list)  # 建議


@dataclass
class ValidationResult:
    """驗證結果」"""

    valid: bool  # 是否通過
    errors: List[ValidationError] = field(default_factory=list)  # 錯誤列表
    warnings: List[str] = field(default_factory=list)  # 警告


class PreValidator:
    """查詢前驗證器」"""

    # 支援的意圖
    SUPPORTED_INTENTS = [
        "QUERY_INVENTORY",
        "QUERY_WORK_ORDER",
        "QUERY_MANUFACTURING_PROGRESS",
        "QUERY_WORKSTATION_OUTPUT",
        "QUERY_SHIPPING",
        "QUERY_STATS",
    ]

    # 必需的參數（按意圖）- 至少需要一個關鍵篩選條件
    REQUIRED_PARAMS = {
        "QUERY_INVENTORY": ["ITEM_NO", "WAREHOUSE_NO"],  # 需要至少一個：料號 或 倉庫
        "QUERY_WORK_ORDER": ["MO_DOC_NO"],
        "QUERY_MANUFACTURING_PROGRESS": ["MO_DOC_NO"],
        "QUERY_WORKSTATION_OUTPUT": ["WORKSTATION"],
        "QUERY_SHIPPING": [],
        "QUERY_STATS": [],
    }

    # 意圖對應的表格
    INTENT_TABLES = {
        "QUERY_INVENTORY": "mart_inventory_wide",
        "QUERY_WORK_ORDER": "mart_work_order_wide",
        "QUERY_MANUFACTURING_PROGRESS": "mart_work_order_wide",
        "QUERY_WORKSTATION_OUTPUT": "mart_work_order_wide",
        "QUERY_SHIPPING": "mart_shipping_wide",
        "QUERY_STATS": "mart_inventory_wide",
    }

    def __init__(self):
        """初始化驗證器」"""
        pass

    async def validate(
        self, query: str, intent: str, entities: Dict[str, str], intent_confidence: float = 1.0
    ) -> ValidationResult:
        """
        驗證查詢

        Args:
            query: 用戶查詢
            intent: 偵測到的意圖
            entities: 提取的實體 {類型: 值}
            intent_confidence: 意圖信心度

        Returns:
            ValidationResult: 驗證結果
        """
        result = ValidationResult(valid=True)

        # 1. 意圖是否支援
        if intent not in self.SUPPORTED_INTENTS:
            result.valid = False
            result.errors.append(
                ValidationError(
                    code=ErrorCode.INTENT_UNCLEAR.value,
                    message=f"不支援的查詢類型: {intent}",
                    suggestions=[f"可用的查詢類型: {', '.join(self.SUPPORTED_INTENTS)}"],
                )
            )
            return result

        # 2. 意圖信心度檢查
        if intent_confidence < 0.6:
            result.valid = False
            result.errors.append(
                ValidationError(
                    code=ErrorCode.INTENT_UNCLEAR.value,
                    message="無法確定查詢意圖",
                    suggestions=self._suggest_intents(query),
                )
            )
            return result

        # 3. 必需的參數檢查 - 改為警告而非阻擋
        required = self.REQUIRED_PARAMS.get(intent, [])
        has_any_param = False

        # 先檢查 entities
        for param in required:
            if param in entities:
                has_any_param = True
                break

        # 如果 entities 為空但查詢文字中包含倉庫或料號，也視為有篩選條件
        if not has_any_param:
            import re

            warehouse_pattern = r"([0-9]{3,4})[倉庫仓庫]"
            part_pattern = r"料號[：:]\s*([A-Za-z0-9\-]+)|([A-Z]{2,4}\d{2,6}-\d{2,6})"

            if re.search(warehouse_pattern, query):
                has_any_param = True
            elif re.search(part_pattern, query):
                has_any_param = True

        if required and not has_any_param:
            result.warnings.append(
                f"注意：查詢缺少明確的篩選條件（{', '.join(required)}），可能返回大量數據"
            )

        # 4. 參數格式檢查
        for param_type, value in entities.items():
            if not self._is_valid_param_format(param_type, value):
                result.valid = False
                result.errors.append(
                    ValidationError(
                        code=ErrorCode.INVALID_PARAM_FORMAT.value,
                        message=f"參數格式不正確: {param_type}",
                        column_name=param_type,
                        value=value,
                        suggestions=self._suggest_param_value(query, param_type),
                    )
                )

        # 5. 查詢範圍檢查（簡單 heuristic）
        if self._is_scope_too_large(query, intent, entities):
            result.warnings.append("查詢範圍可能過大，建議增加篩選條件以獲得更準確的結果")

        # 6. 檢查是否缺少必要的篩選條件
        filter_errors = self._check_missing_filters(query, intent, entities)
        for error in filter_errors:
            result.errors.append(error)
            result.valid = False

        return result

    def _is_valid_param_format(self, param_type: str, value: str) -> bool:
        """檢查參數格式是否正確」"""
        if not value:
            return False

        # 工作站格式
        if param_type == "WORKSTATION":
            import re

            return bool(
                re.match(r"^(WC|WCS|WC\d+-[1-9]|WS|ST|WCA|STD|T\d+|W\d{3})[A-Za-z0-9-]*$", value)
            )

        # 料號格式
        if param_type == "ITEM_NO":
            import re

            return bool(re.match(r"^[A-Z0-9]{10,}$", value))

        # 倉庫格式
        if param_type == "WAREHOUSE_NO":
            import re

            return bool(re.match(r"^[A-Z0-9]{2,4}$", value))

        # 工單格式: XX-XXX-XXXXXXXX 或 XX-XXX-XX-XXXXXXXX
        if param_type == "MO_DOC_NO":
            import re

            # 簡單的格式檢查：2-3個字母-2個以上字母/數字-2個以上數字-8個以上數字
            parts = value.split("-")
            if len(parts) >= 3:
                # 檢查第一部分：2-3個字母
                if 2 <= len(parts[0]) <= 3 and parts[0].isalpha() and parts[0].isupper():
                    # 檢查最後部分：8個以上數字
                    if parts[-1].isdigit() and len(parts[-1]) >= 8:
                        # 檢查中間部分：至少2個字符
                        middle = "-".join(parts[1:-1])
                        if len(middle) >= 2 and all(c.isalnum() or c == "-" for c in middle):
                            return True
            return False

        return True

    def _is_scope_too_large(self, query: str, intent: str, entities: Dict[str, str]) -> bool:
        """檢查查詢範圍是否過大"""
        # 沒有任何篩選條件
        if not entities:
            # 進一步檢查查詢文字是否包含篩選條件
            import re

            warehouse_pattern = r"([0-9]{3,4})[倉庫仓庫]"
            part_pattern = r"料號[：:]\s*([A-Za-z0-9\-]+)|([A-Z]{2,4}\d{2,6}-\d{2,6})"
            if re.search(warehouse_pattern, query) or re.search(part_pattern, query):
                # 查詢文字中有篩選條件，不視為範圍過大
                pass
            else:
                # 某些意圖需要篩選條件
                if intent in ["QUERY_INVENTORY", "QUERY_MANUFACTURING_PROGRESS"]:
                    return True

        # 檢查是否包含範圍過大的關鍵詞
        large_keywords = ["所有", "全部", "everything", "all"]
        if any(kw in query for kw in large_keywords):
            # 進一步檢查是否有限定詞
            limit_keywords = ["料號", " warehouse", "倉庫", "地點", "location"]
            has_limit = any(kw in query for kw in limit_keywords)

            # 數量篩選條件也是有效限定
            quantity_keywords = [
                "為0",
                "等於0",
                "大於",
                "小於",
                "大於1000",
                "小於10",
                ">1000",
                "<10",
                "庫存數量",
            ]
            has_quantity_filter = any(kw in query for kw in quantity_keywords)

            if not has_limit and not has_quantity_filter:
                return True

        return False

    def _check_missing_filters(
        self, query: str, intent: str, entities: Dict[str, str]
    ) -> List[ValidationError]:
        """檢查是否缺少必要的篩選條件"""
        errors = []

        # 第6號場景: "查詢單位為PC的所有料號庫存"
        # 只有單位，沒有倉庫或料號
        if intent == "QUERY_INVENTORY":
            has_unit = "UNIT" in entities
            has_item = "ITEM_NO" in entities
            has_warehouse = "WAREHOUSE_NO" in entities

            # 如果只有單位，沒有其他限定
            if has_unit and not has_item and not has_warehouse:
                errors.append(
                    ValidationError(
                        code=ErrorCode.QUERY_SCOPE_TOO_LARGE.value,
                        message="查詢語義不清：請問您想查詢哪個倉庫或料號的庫存？",
                        suggestions=[
                            "請指定倉庫編號（如：8802、2101）",
                            "或指定料號（如：10-0001）",
                        ],
                    )
                )

        # 第9號場景: "查詢所有料號的現有庫存"
        # 沒有任何限定範圍
        all_keywords = ["所有", "全部", "everything", "all", "現有庫存"]
        if any(kw in query for kw in all_keywords):
            # 檢查是否有篩選條件（從 entities 或 query text）
            has_filter = bool(entities)
            if not has_filter:
                import re

                warehouse_pattern = r"([0-9]{3,4})[倉庫仓庫]"
                part_pattern = r"料號[：:]\s*([A-Za-z0-9\-]+)|([A-Z]{2,4}\d{2,6}-\d{2,6})"
                quantity_pattern = r"為\d+|等於\d+|大於\d+|小於\d+|[<>=]\d+"

                if (
                    re.search(warehouse_pattern, query)
                    or re.search(part_pattern, query)
                    or re.search(quantity_pattern, query)
                ):
                    has_filter = True

            if not has_filter:
                errors.append(
                    ValidationError(
                        code=ErrorCode.QUERY_SCOPE_TOO_LARGE.value,
                        message="查詢範圍過大：請增加篩選條件",
                        suggestions=[
                            "請指定料號範圍（如：10-0001 到 10-0010）",
                            "或指定倉庫編號",
                            "或分批查詢（如：先查前100筆）",
                        ],
                    )
                )

        # 場景5: 查詢所有庫存數量為0的料號 - 有數量篩選條件，允許通過但提示分頁
        zero_keywords = [
            "等於0",
            "等於零",
            "為0",
            "為零",
            "庫存0",
            "庫存為0",
            "數量為0",
            "數量等於0",
        ]
        if any(kw in query for kw in zero_keywords):
            # 有數量篩選，這是有效查詢，只是數據量大
            # 不返回錯誤，只在後續處理時添加分頁提示
            pass

        # 場景6: 查詢庫存數量大於1000的料號 - 有數量篩選條件
        gt_keywords = ["大於1000", "超過1000", ">1000"]
        if any(kw in query for kw in gt_keywords):
            pass

        # 場景8: 查詢庫存數量小於10的料號 - 有數量篩選條件
        lt_keywords = ["小於10", "少於10", "<10", "不足10"]
        if any(kw in query for kw in lt_keywords):
            pass

        return errors

    def _suggest_intents(self, query: str) -> List[str]:
        """建議可能的意圖」"""
        suggestions = []

        if any(kw in query for kw in ["庫存", "在庫", "stock", "inventory"]):
            suggestions.append("您是想查詢庫存嗎？")

        if any(kw in query for kw in ["工站", "工作站", "WC", "station"]):
            suggestions.append("您是想查詢工作站嗎？")

        if any(kw in query for kw in ["工單", "WO", "work order"]):
            suggestions.append("您是想查詢工單嗎？")

        if any(kw in query for kw in ["出貨", "出荷", "ship"]):
            suggestions.append("您是想查詢出貨嗎？")

        if not suggestions:
            suggestions = [
                "您可以說：'查詢 8802 倉庫的庫存'",
                "您可以說：'WC77 工作站生產了哪些料號'",
                "您可以說：'查詢工單 WO-2025-001 的進度'",
            ]

        return suggestions

    def _suggest_param_value(self, query: str, param_type: str) -> List[str]:
        """建議參數值」"""
        suggestions = []

        if param_type == "WORKSTATION":
            suggestions = ["工作站編號範例：WC77、WC01-A、WS01", "可用工作站：請參考系統設定"]
        elif param_type == "ITEM_NO":
            suggestions = ["料號格式：15-18 碼英數字", "料號範例：81199GG01080"]
        elif param_type == "WAREHOUSE_NO":
            suggestions = ["倉庫編號格式：2-4 碼", "倉庫範例：8802、W01、WH01"]
        elif param_type == "MO_DOC_NO":
            suggestions = ["工單格式：XXX-XX-XXXXXXXX", "工單範例：WO-ABC-12345678"]

        return suggestions

    def get_intent_table(self, intent: str) -> Optional[str]:
        """獲取意圖對應的表格名稱」"""
        return self.INTENT_TABLES.get(intent)


async def demo():
    """演示」"""
    validator = PreValidator()

    queries = [
        (
            "能查出工作站WC77 生產那些料號嗎？",
            "QUERY_WORKSTATION_OUTPUT",
            {"WORKSTATION": "WC77"},
            0.95,
        ),
        ("我想查庫存", "QUERY_INVENTORY", {}, 0.5),
        ("查所有庫存", "QUERY_INVENTORY", {}, 0.9),
    ]

    for query, intent, entities, confidence in queries:
        print(f"\n=== Query: {query} ===")
        result = await validator.validate(query, intent, entities, confidence)

        if result.valid:
            print("✅ 驗證通過")
            table = validator.get_intent_table(intent)
            print(f"   表格: {table}")
        else:
            print("❌ 驗證失敗")
            for error in result.errors:
                print(f"   [{error.code}] {error.message}")
                for suggestion in error.suggestions:
                    print(f"      → {suggestion}")

        if result.warnings:
            print("⚠️  警告:")
            for warning in result.warnings:
                print(f"   {warning}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
