# 代碼功能說明: 轉譯引擎 - 專業術語轉換
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""轉譯引擎 - 將自然語言轉換為專業術語"""

import re
from typing import Optional
from pydantic import BaseModel


class TranslationResult(BaseModel):
    """轉譯結果"""

    tlf19: Optional[str] = None
    tlf19_description: Optional[str] = None
    time_expr: Optional[str] = None
    time_description: Optional[str] = None
    part_number: Optional[str] = None
    quantity: Optional[int] = None
    table_name: Optional[str] = None
    warehouse: Optional[str] = None


class Translator:
    """轉譯引擎"""

    TRANSACTION_TYPE_MAP = {
        # 採購相關 -> 101
        "採購": "101",
        "買": "101",
        "買進": "101",
        "進": "101",
        "進貨": "101",
        "收料": "101",
        "入庫": "102",
        "完工入庫": "102",
        # 生產領料 -> 201
        "領料": "201",
        "生產領料": "201",
        "領用": "201",
        # 銷售相關 -> 202
        "銷售": "202",
        "賣": "202",
        "賣出": "202",
        "出貨": "202",
        "出庫": "202",
        # 報廢 -> 301
        "報廢": "301",
        "報損": "301",
        "損耗": "301",
    }

    TRANSACTION_DESCRIPTION = {
        "101": "採購進貨",
        "102": "完工入庫",
        "201": "生產領料",
        "202": "銷售出庫",
        "301": "庫存報廢",
    }

    TABLE_MAP = {
        "101": "tlf_file",
        "102": "tlf_file",
        "201": "tlf_file",
        "202": "tlf_file",
        "301": "tlf_file",
        "inventory": "img_file",
        "庫存": "img_file",
    }

    TIME_PATTERN_MAP = {
        r"上[個]?月[份]?": "DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
        r"本[個]?月[份]?": "DATE_FORMAT(CURDATE(), '%Y-%m')",
        r"今[年]?": "YEAR(CURDATE())",
        r"去[年]?": "YEAR(CURDATE()) - 1",
        r"最近(\d+)[天日]": "DATE_SUB(CURDATE(), INTERVAL {0} DAY)",
        r"最近(\d+)[個]?月": "DATE_SUB(CURDATE(), INTERVAL {0} MONTH)",
    }

    def __init__(self):
        self._logger = None

    def translate_tlf19(self, text: str) -> Optional[str]:
        """轉譯交易類別"""
        for keyword, code in self.TRANSACTION_TYPE_MAP.items():
            if keyword in text:
                return code
        return None

    def translate_time(self, text: str) -> Optional[str]:
        """轉譯時間表達式"""
        for pattern, sql in self.TIME_PATTERN_MAP.items():
            match = re.search(pattern, text)
            if match:
                if "{0}" in sql:
                    sql = sql.format(match.group(1))
                return sql
        return None

    def extract_part_number(self, text: str) -> Optional[str]:
        """提取料號"""
        patterns = [
            r"([A-Z]{2,4}-\d{2,6})",  # ABC-123
            r"料號[：:\s]*([A-Z0-9-]+)",  # 料號：ABC-123
            r"品號[：:\s]*([A-Z0-9-]+)",  # 品號：ABC-123
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).upper()
        return None

    def extract_quantity(self, text: str) -> Optional[int]:
        """提取數量"""
        patterns = [
            r"(\d+)\s*(?:個|件|PCS|pcs|kg|KG|公斤)",
            r"(\d+)\s*(?:合計|總計|共)",
            r"共\s*(\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None

    def extract_warehouse(self, text: str) -> Optional[str]:
        """提取倉庫"""
        warehouse_map = {
            "原料倉": "W01",
            "成品倉": "W02",
            "半成品倉": "W03",
            "不良品倉": "W04",
            "回收倉": "W05",
        }
        for name, warehouse in warehouse_map.items():
            if name in text:
                return warehouse

        patterns = [
            r"[倉](W\d{2})",
            r"(W\d{2})[倉]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    def translate(self, instruction: str) -> TranslationResult:
        """完整轉譯"""
        tlf19 = self.translate_tlf19(instruction)
        time_expr = self.translate_time(instruction)
        table_name = (
            self.TABLE_MAP.get(tlf19) if tlf19 else ("img_file" if "庫存" in instruction else None)
        )

        return TranslationResult(
            tlf19=tlf19,
            tlf19_description=self.TRANSACTION_DESCRIPTION.get(tlf19 or "", ""),
            time_expr=time_expr,
            part_number=self.extract_part_number(instruction),
            quantity=self.extract_quantity(instruction),
            table_name=table_name,
            warehouse=self.extract_warehouse(instruction),
        )


if __name__ == "__main__":
    translator = Translator()

    test_cases = [
        "RM05-008 上月買進多少",
        "ABC-123 上個月採購數量",
        "RM05-008 庫存還有多少",
        "RM05-008 最近7天銷售情況",
    ]

    for instruction in test_cases:
        result = translator.translate(instruction)
        print(f"\n指令: {instruction}")
        print(f"  tlf19: {result.tlf19} ({result.tlf19_description})")
        print(f"  time: {result.time_expr}")
        print(f"  part_number: {result.part_number}")
        print(f"  quantity: {result.quantity}")
