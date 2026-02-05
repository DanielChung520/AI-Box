# 代碼功能說明: 轉譯引擎 - 專業術語轉換
# 創建日期: 2026-01-31
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-05

"""轉譯引擎 - 將自然語言轉換為專業術語（支持關鍵詞匹配 + LLM 語義轉譯）"""

import logging
import re
from typing import Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
    material_category: Optional[str] = None


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

    MATERIAL_CATEGORY_MAP = {
        "塑料件": "plastic",
        "塑膠件": "plastic",
        "塑膠": "plastic",
        "塑料": "plastic",
        "金屬件": "metal",
        "金屬": "metal",
        "電子件": "electronic",
        "電子": "electronic",
        "成品": "finished",
        "半成品": "semi",
        "原料": "raw",
        "不良品": "defective",
        "回收料": "recycled",
    }

    TIME_PATTERN_MAP = {
        r"上[個]?月[份]?": "DATE_SUB(CURDATE(), INTERVAL 1 MONTH)",
        r"本[個]?月[份]?": "DATE_FORMAT(CURDATE(), '%Y-%m')",
        r"今[年]?": "YEAR(CURDATE())",
        r"去[年]?": "YEAR(CURDATE()) - 1",
        r"最近(\d+)[天日]": "DATE_SUB(CURDATE(), INTERVAL {0} DAY)",
        r"最近(\d+)[個]?月": "DATE_SUB(CURDATE(), INTERVAL {0} MONTH)",
    }

    def __init__(self, use_semantic_translator: bool = False):
        """初始化轉譯引擎

        Args:
            use_semantic_translator: 是否使用語義轉譯 Agent（LLM）
                True: 使用 LLM 進行語義理解（更靈活，但較慢）
                False: 使用關鍵詞匹配（快速，穩定）
        """
        self._use_semantic_translator = use_semantic_translator
        self._logger = logger
        self._semantic_translator = None

        # 如果啟用語義轉譯，延遲初始化
        if self._use_semantic_translator:
            try:
                from .semantic_translator import SemanticTranslatorAgent

                self._semantic_translator = SemanticTranslatorAgent()
                logger.info("語義轉譯 Agent 已啟用")
            except Exception as e:
                logger.warning(f"無法初始化語義轉譯 Agent，將使用關鍵詞匹配: {e}")
                self._use_semantic_translator = False

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
            r"([A-Z]{2,4}-?\d{2,6}(?:-\d{2,6})?)",  # ABC-123 或 RM05-008 或 ABC-456-789
            r"([A-Z]{2,4}\d{2,6}(?:-\d{2,6})?)",  # RM05008 或 RM05008-009
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
            r"(?:合計|總計|共)\s*(\d+)",
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

    def extract_material_category(self, text: str) -> Optional[str]:
        """提取物料類別"""
        for keyword, category in self.MATERIAL_CATEGORY_MAP.items():
            if keyword in text:
                return category
        return None

    def extract_warehouse(self, text: str) -> Optional[str]:
        """提取倉庫"""
        warehouse_map = {
            "原料倉": "W01",
            "成品倉": "W02",
            "半成品倉": "W03",
            "不良品倉": "W04",
            "回收倉": "W05",
            "庫房": None,  # 通用倉庫，不指定具體代碼
            "倉庫": None,
        }
        # 按長度降序排列，確保更長的名稱先被匹配
        sorted_warehouses = sorted(warehouse_map.items(), key=lambda x: len(x[0]), reverse=True)
        for name, warehouse in sorted_warehouses:
            if name == text or text.endswith(name):
                return warehouse

        patterns = [
            r"[倉](W\d{2})",
            r"(W\d{2})[倉]",
            r"(W\d{2})",  # 單獨的倉庫代碼
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    async def translate(self, instruction: str) -> TranslationResult:
        """完整轉譯（支持關鍵詞匹配和語義轉譯）

        Args:
            instruction: 用戶指令

        Returns:
            轉譯結果
        """
        # 如果啟用語義轉譯，使用 LLM
        if self._use_semantic_translator and self._semantic_translator:
            return await self._translate_with_llm(instruction)

        # 否則使用關鍵詞匹配（原有邏輯）
        return self._translate_with_keywords(instruction)

    def _translate_with_keywords(self, instruction: str) -> TranslationResult:
        """使用關鍵詞匹配進行轉譯（原有邏輯）"""
        tlf19 = self.translate_tlf19(instruction)
        time_expr = self.translate_time(instruction)
        table_name = (
            self.TABLE_MAP.get(tlf19)
            if tlf19
            else (
                "img_file"
                if "庫存" in instruction or "還有多少" in instruction or "塑料件" in instruction
                else None
            )
        )

        material_category = self.extract_material_category(instruction)

        return TranslationResult(
            tlf19=tlf19,
            tlf19_description=self.TRANSACTION_DESCRIPTION.get(tlf19 or "", ""),
            time_expr=time_expr,
            part_number=self.extract_part_number(instruction),
            quantity=self.extract_quantity(instruction),
            table_name=table_name,
            warehouse=self.extract_warehouse(instruction),
            material_category=material_category,
        )

    async def _translate_with_llm(self, instruction: str) -> TranslationResult:
        """使用 LLM 語義轉譯進行轉譯

        Args:
            instruction: 用戶指令

        Returns:
            轉譯結果（與關鍵詞匹配相同的格式）
        """
        try:
            # 檢查語義轉譯器是否可用
            if self._semantic_translator is None:
                logger.warning("語義轉譯 Agent 未初始化，回退到關鍵詞匹配")
                return self._translate_with_keywords(instruction)

            # 調用語義轉譯 Agent
            semantic_result = await self._semantic_translator.translate(instruction)

            # 映射到 TranslationResult 格式
            constraints = semantic_result.constraints
            schema_binding = semantic_result.schema_binding

            # 從 constraints 提取信息
            part_number = constraints.material_id
            warehouse = constraints.inventory_location
            transaction_type = constraints.transaction_type
            quantity = constraints.quantity

            # 從 schema_binding 提取表名
            table_name = (
                schema_binding.primary_table or schema_binding.tables[0]
                if schema_binding.tables
                else None
            )

            # 處理交易類型
            tlf19 = transaction_type
            tlf19_description = self.TRANSACTION_DESCRIPTION.get(transaction_type or "", "")

            # 時間表達式（從 constraints.time_range 提取）
            time_expr = None
            if constraints.time_range:
                # 簡化處理：如果有時間範圍，提取為 SQL 表達式
                if "start" in constraints.time_range:
                    time_expr = f">= '{constraints.time_range['start']}'"

            # 物料類別（簡化處理）
            material_category = None
            if "plastic" in instruction.lower() or "塑料" in instruction:
                material_category = "plastic"
            elif "metal" in instruction.lower() or "金屬" in instruction:
                material_category = "metal"

            # 處理需要確認的情況
            if semantic_result.validation.requires_confirmation:
                logger.warning(f"語義轉譯需要確認: {semantic_result.validation.notes}")

            return TranslationResult(
                tlf19=tlf19,
                tlf19_description=tlf19_description,
                time_expr=time_expr,
                part_number=part_number,
                quantity=quantity,
                table_name=table_name,
                warehouse=warehouse,
                material_category=material_category,
            )

        except Exception as e:
            logger.error(f"LLM 語義轉譯失敗，回退到關鍵詞匹配: {e}", exc_info=True)
            # 回退到關鍵詞匹配
            return self._translate_with_keywords(instruction)


if __name__ == "__main__":
    import asyncio

    async def main():
        # 測試關鍵詞匹配（默認）
        print("=" * 70)
        print("測試 1: 關鍵詞匹配（原有邏輯）")
        print("=" * 70)
        translator = Translator(use_semantic_translator=False)

        test_cases = [
            "RM05-008 上月買進多少",
            "ABC-123 上個月採購數量",
            "RM05-008 庫存還有多少",
            "RM05-008 最近7天銷售情況",
        ]

        for instruction in test_cases:
            result = await translator.translate(instruction)
            print(f"\n指令: {instruction}")
            print(f"  tlf19: {result.tlf19} ({result.tlf19_description})")
            print(f"  time: {result.time_expr}")
            print(f"  part_number: {result.part_number}")
            print(f"  quantity: {result.quantity}")

        # 測試語義轉譯（新增）
        print("\n" + "=" * 70)
        print("測試 2: 語義轉譯（LLM）")
        print("=" * 70)
        translator_llm = Translator(use_semantic_translator=True)

        test_cases_llm = [
            "RM05-008 上月買進多少",
            "查詢 W01 倉庫的塑料件庫存",
            "庫存夠嗎",
        ]

        for instruction in test_cases_llm:
            print(f"\n指令: {instruction}")
            try:
                result = await translator.translate(instruction)
                print(f"  tlf19: {result.tlf19} ({result.tlf19_description})")
                print(f"  table_name: {result.table_name}")
                print(f"  part_number: {result.part_number}")
                print(f"  warehouse: {result.warehouse}")
            except Exception as e:
                print(f"  ❌ 轉譯失敗: {e}")

    asyncio.run(main())
