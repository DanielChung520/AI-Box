# 代碼功能說明: 代碼字典服務
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-31
# 用途: 提供程式代碼、倉庫代碼、料號的精確對應

"""
代碼字典服務

功能：
1. 倉庫代碼對照（W01 → 原料倉）
2. 料號格式驗證（XX-XXXX）
3. 程式代碼對照（AXMT520 → 出貨訂單查詢）
4. Table Alias 對照（inag_t → tlf_file）

使用方式：
    from data_agent.code_dictionary import CodeDictionary

    cd = CodeDictionary()
    result = cd.lookup("W01")
    # {"code": "W01", "type": "warehouse", "name": "原料倉", "table": "img_file", ...}
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class CodeDictionary:
    """代碼字典服務 - 支援程式代碼、倉庫代碼、料號的精確對應"""

    def __init__(self, dictionary_path: str = None):
        self._dictionary: Dict[str, Any] = {}
        self._patterns: List[Dict[str, Any]] = []
        self._code_aliases: Dict[str, str] = {}
        self._load_dictionary(dictionary_path)

    def _load_dictionary(self, dictionary_path: str = None):
        """載入代碼字典"""
        if dictionary_path is None:
            dictionary_path = Path(__file__).parent / "code_dictionary.json"

        try:
            with open(dictionary_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._parse_dictionary(data)
        except FileNotFoundError:
            self._use_default_dictionary()
        except json.JSONDecodeError as e:
            print(f"[CodeDictionary] JSON 解析錯誤: {e}")
            self._use_default_dictionary()

    def _parse_dictionary(self, data: Dict[str, Any]):
        """解析字典資料"""
        self._dictionary.clear()
        self._patterns.clear()
        self._code_aliases.clear()

        if "codes" in data:
            for code, info in data["codes"].items():
                self._dictionary[code.upper()] = {**info, "code": code.upper()}

        if "code_patterns" in data:
            for pattern_info in data["code_patterns"]:
                self._patterns.append(pattern_info)

        if "code_aliases" in data:
            self._code_aliases = data["code_aliases"]

    def _use_default_dictionary(self):
        """使用預設字典（倉庫代碼 W01-W05）"""
        self._dictionary = {
            "W01": {
                "code": "W01",
                "type": "warehouse",
                "name": "原料倉",
                "description": "原料倉庫",
                "table": "img_file",
                "field": "img02",
            },
            "W02": {
                "code": "W02",
                "type": "warehouse",
                "name": "半成品倉",
                "description": "半成品倉庫",
                "table": "img_file",
                "field": "img02",
            },
            "W03": {
                "code": "W03",
                "type": "warehouse",
                "name": "成品倉",
                "description": "成品倉庫",
                "table": "img_file",
                "field": "img02",
            },
            "W04": {
                "code": "W04",
                "type": "warehouse",
                "name": "不良品倉",
                "description": "不良品倉庫",
                "table": "img_file",
                "field": "img02",
            },
            "W05": {
                "code": "W05",
                "type": "warehouse",
                "name": "樣品倉",
                "description": "樣品倉庫",
                "table": "img_file",
                "field": "img02",
            },
        }

        self._patterns = [
            {
                "pattern": r"^W0[1-5]$",
                "type": "warehouse",
                "description": "倉庫代碼（W01-W05）",
                "default_table": "img_file",
                "default_field": "img02",
            },
            {
                "pattern": r"^\d{2}-\d{4}$",
                "type": "item_code",
                "description": "料號格式（XX-XXXX）",
                "default_table": "ima_file",
                "default_field": "ima01",
            },
            {
                "pattern": r"^[A-Z]{4}\d{3}$",
                "type": "program_code",
                "description": "Tiptop 程式代碼",
                "default_table": None,
            },
            {
                "pattern": r"^[a-z_][a-z0-9_]*$",
                "type": "table_alias",
                "description": "資料表別名（小寫）",
                "default_table": None,
            },
        ]

    def lookup(self, code: str) -> Optional[Dict[str, Any]]:
        """
        查詢代碼含義

        Args:
            code: 代碼字串（如 W01、10-0001、AXMT520）

        Returns:
            代碼資訊字典，若未找到返回 None
        """
        if not code:
            return None

        code_upper = code.upper()

        if code_upper in self._dictionary:
            return self._dictionary[code_upper]

        if code_upper in self._code_aliases:
            actual_table = self._code_aliases[code_upper]
            return {
                "code": code_upper,
                "type": "table_alias",
                "actual_table": actual_table,
                "description": f"表別名：{code_upper} → {actual_table}",
            }

        for pattern_info in self._patterns:
            if re.match(pattern_info["pattern"], code):
                result = {
                    "code": code,
                    "type": pattern_info["type"],
                    "description": pattern_info["description"],
                    "source": "pattern",
                }
                if "default_table" in pattern_info:
                    result["default_table"] = pattern_info["default_table"]
                if "default_field" in pattern_info:
                    result["default_field"] = pattern_info["default_field"]
                return result

        return None

    def lookup_table(self, code: str) -> Optional[str]:
        """
        查詢代碼對應的資料表

        Args:
            code: 代碼字串

        Returns:
            資料表名稱，若未找到返回 None
        """
        info = self.lookup(code)
        if info:
            if "table" in info:
                return info["table"]
            if "default_table" in info:
                return info["default_table"]
            if "actual_table" in info:
                return info["actual_table"]
        return None

    def lookup_field(self, code: str) -> Optional[str]:
        """
        查詢代碼對應的欄位

        Args:
            code: 代碼字串

        Returns:
            欄位名稱，若未找到返回 None
        """
        info = self.lookup(code)
        if info:
            if "field" in info:
                return info["field"]
            if "default_field" in info:
                return info["default_field"]
        return None

    def validate_code(self, code: str) -> Dict[str, Any]:
        """
        驗證代碼格式與有效性

        Args:
            code: 代碼字串

        Returns:
            驗證結果字典
        """
        info = self.lookup(code)
        if info:
            return {
                "valid": True,
                "code": code,
                "type": info.get("type", "unknown"),
                "name": info.get("name", info.get("description", "")),
                "table": info.get("table") or info.get("default_table") or info.get("actual_table"),
            }
        else:
            return {"valid": False, "code": code, "reason": "unknown_code"}

    def is_valid_warehouse(self, code: str) -> bool:
        """檢查是否為有效的倉庫代碼"""
        info = self.lookup(code)
        return info is not None and info.get("type") == "warehouse"

    def is_valid_item_code(self, code: str) -> bool:
        """檢查是否為有效的料號格式"""
        return bool(re.match(r"^\d{2}-\d{4}$", code))

    def get_warehouse_name(self, code: str) -> Optional[str]:
        """取得倉庫名稱"""
        info = self.lookup(code)
        if info and info.get("type") == "warehouse":
            return info.get("name")
        return None

    def get_all_warehouses(self) -> List[Dict[str, Any]]:
        """取得所有倉庫代碼列表"""
        warehouses = []
        for code, info in self._dictionary.items():
            if info.get("type") == "warehouse":
                warehouses.append(info)
        return warehouses

    def resolve_alias(self, alias: str) -> Optional[str]:
        """
        解析表別名

        Args:
            alias: 別名字串（如 inag_t）

        Returns:
            實際表名稱，若未找到返回 None
        """
        if alias in self._code_aliases:
            return self._code_aliases[alias]
        return None


def test_code_dictionary():
    """測試代碼字典功能"""
    cd = CodeDictionary()

    test_cases = [
        ("W01", "warehouse", "原料倉"),
        ("W02", "warehouse", "半成品倉"),
        ("W03", "warehouse", "成品倉"),
        ("10-0001", "item_code", None),
        ("UNKNOWN", None, None),
    ]

    print("=" * 60)
    print("CodeDictionary 測試")
    print("=" * 60)

    all_passed = True
    for code, expected_type, expected_name in test_cases:
        result = cd.lookup(code)

        if expected_type is None:
            if result is None:
                print(f"✅ {code}: 正確識別為未知代碼")
            else:
                print(f"❌ {code}: 預期 None，但返回 {result}")
                all_passed = False
        else:
            if result and result.get("type") == expected_type:
                name = result.get("name", result.get("description", ""))
                if expected_name is None or name == expected_name:
                    print(f"✅ {code}: {result.get('type')} - {name}")
                else:
                    print(f"❌ {code}: 名稱不符，預期 {expected_name}，得到 {name}")
                    all_passed = False
            else:
                print(f"❌ {code}: 類型不符或未找到")
                all_passed = False

    print()
    if all_passed:
        print("✅ 所有測試通過！")
    else:
        print("❌ 有測試失敗")

    return all_passed


if __name__ == "__main__":
    test_code_dictionary()
