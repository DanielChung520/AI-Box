# -*- coding: utf-8 -*-
# 代碼功能說明: 物料類別提取器
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""MaterialCategoryExtractor - 獨立物料類別提取模組

職責：
- 提取物料類別（原料、半成品、成品、輔料等）
- 支持企業級物料分類
- 獨立模組，可測試，可移植

物料類別：
- RAW: 原料
- SEMI_FINISHED: 半成品
- FINISHED: 成品
- PACKAGING: 包裝材料
- CONSUMABLE: 消耗品
- SPARE_PART: 備品備件
- SUBMATERIAL: 輔料
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class CategoryMatch:
    """物料類別匹配結果"""

    category_code: str  # 類別代碼（如：RAW, FINISHED）
    category_name: str  # 類別名稱（如：原料、成品）
    matched_keyword: Optional[str] = None
    confidence: float = 1.0


@dataclass
class CategoryClarification:
    """物料類別澄清結果（用於模糊表達）"""

    need_clarification: bool = False
    fuzzy_keyword: Optional[str] = None
    question: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class MaterialCategoryExtractor:
    """獨立物料類別提取器

    特點：
    - 純規則引擎，無 LLM 依賴
    - 支持簡體/繁體中文
    - 支持企業級物料分類
    - 獨立模組，可測試，可移植
    - 可配置規則
    """

    # ========== 基礎物料類別 ==========

    # 原料類別
    RAW_MATERIAL = {
        "RAW": [
            "原料",
            "原材料",
            "原物料",
            "原料材",
            "raw material",
            "raw materials",
            "原料料",
            "基礎原料",
        ]
    }

    # 半成品類別
    SEMI_FINISHED = {
        "SEMI_FINISHED": [
            "半成品",
            "半製品",
            "半成品",
            "在製品",
            "wip",
            "work in progress",
            "生產中",
            "加工中",
            "中間品",
        ]
    }

    # 成品類別
    FINISHED_GOODS = {
        "FINISHED": [
            "成品",
            "製成品",
            "完成品",
            "finished goods",
            "finished product",
            "最終產品",
            "產品",
        ]
    }

    # 包裝材料類別
    PACKAGING = {
        "PACKAGING": [
            "包裝材料",
            "包裝",
            "包材",
            "包裝盒",
            "包裝袋",
            "紙盒",
            "紙箱",
            "packaging",
            "packing material",
            "外包裝",
            "內包裝",
        ]
    }

    # 消耗品類別
    CONSUMABLE = {
        "CONSUMABLE": [
            "消耗品",
            "耗材",
            "消耗材料",
            "consumable",
            "consumables",
            "用完即丟",
            "一次性用品",
        ]
    }

    # 備品備件類別
    SPARE_PART = {
        "SPARE_PART": [
            "備品",
            "備件",
            "配件",
            "零件",
            "spare part",
            "spare parts",
            "維修零件",
            "替換零件",
        ]
    }

    # 輔料類別
    SUBMATERIAL = {
        "SUBMATERIAL": [
            "輔料",
            "副料",
            "間接材料",
            "supporting material",
            "auxiliary material",
            "生產輔料",
            "工藝輔料",
        ]
    }

    # ========== 細分物料類別（按材質） ==========

    # 塑料/塑膠類
    PLASTIC = {
        "PLASTIC": [
            "塑料",
            "塑膠",
            "塑膠件",
            "塑料件",
            "塑膠原料",
            "塑膠粒子",
            "plastic",
            "塑膠材料",
            "高分子材料",
        ]
    }

    # 金屬類
    METAL = {
        "METAL": [
            "金屬",
            "金屬件",
            "金屬材料",
            "五金",
            "鋼材",
            "鋁材",
            "銅材",
            "metal",
            "金屬製品",
            "有色金屬",
            "黑色金屬",
        ]
    }

    # 電子類
    ELECTRONIC = {
        "ELECTRONIC": [
            "電子",
            "電子元件",
            "電子零件",
            "電子材料",
            "electronic",
            "electronic components",
            "半導體",
            "ic",
            "電容",
            "電阻",
        ]
    }

    # 化學類
    CHEMICAL = {
        "CHEMICAL": [
            "化工原料",  # 放在前面確保優先匹配
            "化學原料",
            "化工材料",
            "化學材料",
            "化學",
            "化學品",
            "化工",
            "chemical",
            "溶劑",
            "涂料",
            "膠水",
            "粘合劑",
        ]
    }

    # 紙類
    PAPER = {
        "PAPER": [
            "紙張",  # 放在前面確保優先匹配
            "紙材",
            "紙製品",
            "paper",
            "說明書",
        ]
    }

    # 紡織類
    TEXTILE = {
        "TEXTILE": [
            "紡織",
            "布料",
            "紡織品",
            "fabric",
            "布料",
            "紗線",
            " yarn",
            "織物",
        ]
    }

    # ========== 企業級分類 ==========

    # ABC 分類
    ABC_CLASS = {
        "A_CLASS": ["A類", "A級", "A類物料", "A級物料", "重要物料"],
        "B_CLASS": ["B類", "B級", "B類物料", "B級物料", "一般物料"],
        "C_CLASS": ["C類", "C級", "C類物料", "C級物料", "次要物料"],
    }

    # 採購分類
    PROCUREMENT_CLASS = {
        "MRO": ["mro", "維護維修", "維修用品", "maintenance", "維護物料"],
        "RAW_DIRECT": ["直接原料", "主要原料", "直接材料"],
        "INDIRECT": ["間接物料", "間接材料", "輔助物料"],
        "CAPITAL": ["資本物料", "設備", "固定資產"],
    }

    # ========== 模糊表達（需要 Clarification） ==========

    FUZZY_EXPRESSIONS = {
        "fuzzy_material": ["物料", "材料", "東西", "貨品"],
        "fuzzy_type": ["這類", "那類", "這類型的", "那種類型的"],
        "fuzzy_category": ["這個類別", "那個類別", "相關類別"],
    }

    def __init__(self, custom_rules: Optional[Dict[str, List[str]]] = None):
        """初始化物料類別提取器

        Args:
            custom_rules: 自定義規則（可覆蓋預設規則）
        """
        # 按優先級順序定義（索引越大優先級越高）
        # 優先級從低到高
        priority_order = [
            (self.RAW_MATERIAL, 1),  # 最低優先級
            (self.PROCUREMENT_CLASS, 2),  # 採購分類
            (self.SEMI_FINISHED, 3),
            (self.FINISHED_GOODS, 4),
            (self.PACKAGING, 5),  # 包裝材料
            (self.CONSUMABLE, 6),
            (self.SPARE_PART, 7),
            (self.ABC_CLASS, 8),
            (self.TEXTILE, 9),
            (self.SUBMATERIAL, 10),  # 讓 SUBMATERIAL > INDIRECT
            (self.PLASTIC, 11),
            (self.METAL, 12),
            (self.ELECTRONIC, 13),
            (self.CHEMICAL, 14),  # 讓 CHEMICAL > RAW
            (self.PAPER, 15),  # 讓 PAPER > 其他
        ]

        # 反向映射：關鍵詞 -> (類別代碼, 優先級)
        # 確保更高優先級的類別獲勝
        self._keyword_to_category = {}

        for category_dict, priority in priority_order:
            for category_code, keywords in category_dict.items():
                for keyword in keywords:
                    # 只有當關鍵詞不存在或優先級更高时才更新
                    if keyword not in self._keyword_to_category:
                        self._keyword_to_category[keyword] = (category_code, priority)
                    elif self._keyword_to_category[keyword][1] < priority:
                        self._keyword_to_category[keyword] = (category_code, priority)

        # 如果有自定義規則，給予最高優先級
        if custom_rules:
            for category_code, keywords in custom_rules.items():
                for keyword in keywords:
                    self._keyword_to_category[keyword] = (category_code, 100)

        # 模糊表達
        self.FUZZY_KEYWORDS = []
        for keywords in self.FUZZY_EXPRESSIONS.values():
            self.FUZZY_KEYWORDS.extend(keywords)

    def _get_clarification_question(self, fuzzy_type: str) -> tuple:
        """獲取澄清問題和建議"""
        questions = {
            "fuzzy_material": (
                "請問具體是什麼物料？",
                ["原料（塑料、金屬、電子）", "成品", "包裝材料", "消耗品"],
            ),
            "fuzzy_type": (
                "請問具體是哪種類型？",
                ["原料", "半成品", "成品", "包裝材料", "消耗品"],
            ),
            "fuzzy_category": (
                "請問具體是哪個類別？",
                ["按材質：塑料、金屬、電子、紙張", "按ABC：A類、B類、C類"],
            ),
        }
        return questions.get(fuzzy_type, ("請提供具體物料類別", []))

    def extract(self, text: str) -> Optional[CategoryMatch]:
        """提取物料類別

        Args:
            text: 用戶輸入文本

        Returns:
            CategoryMatch 或 None
        """
        # 步驟 1：精確匹配（按關鍵詞長度排序，長的在前）
        sorted_keywords = sorted(
            self._keyword_to_category.keys(),
            key=len,
            reverse=True,
        )

        for keyword in sorted_keywords:
            if keyword in text:
                # _keyword_to_category[keyword] 返回 (category_code, priority)
                category_code = self._keyword_to_category[keyword][0]
                category_name = self._get_category_name(category_code)
                return CategoryMatch(
                    category_code=category_code,
                    category_name=category_name,
                    matched_keyword=keyword,
                    confidence=1.0,
                )

        return None

    def _get_category_name(self, category_code: str) -> str:
        """獲取類別名稱"""
        category_names = {
            "RAW": "原料",
            "SEMI_FINISHED": "半成品",
            "FINISHED": "成品",
            "PACKAGING": "包裝材料",
            "CONSUMABLE": "消耗品",
            "SPARE_PART": "備品備件",
            "SUBMATERIAL": "輔料",
            "PLASTIC": "塑料/塑膠",
            "METAL": "金屬",
            "ELECTRONIC": "電子",
            "CHEMICAL": "化學品",
            "PAPER": "紙張",
            "TEXTILE": "紡織",
            "A_CLASS": "A類物料",
            "B_CLASS": "B類物料",
            "C_CLASS": "C類物料",
            "MRO": "維護維修物料",
            "RAW_DIRECT": "直接原料",
            "INDIRECT": "間接物料",
            "CAPITAL": "資本物料",
        }
        return category_names.get(category_code, category_code)

    def check_fuzzy(self, text: str) -> CategoryClarification:
        """檢查模糊表達（返回 Clarification）"""
        for fuzzy_type, keywords in self.FUZZY_EXPRESSIONS.items():
            for keyword in keywords:
                if keyword in text:
                    question, suggestions = self._get_clarification_question(fuzzy_type)
                    return CategoryClarification(
                        need_clarification=True,
                        fuzzy_keyword=keyword,
                        question=question,
                        suggestions=suggestions,
                    )
        return CategoryClarification(need_clarification=False)

    def extract_with_clarification(self, text: str) -> tuple:
        """提取物料類別（包含 Clarification）

        Returns:
            tuple: (CategoryMatch or None, CategoryClarification)
        """
        # 先檢查模糊表達
        clarification = self.check_fuzzy(text)
        if clarification.need_clarification:
            return None, clarification

        # 提取精確類別
        match = self.extract(text)
        return match, CategoryClarification(need_clarification=False)

    def extract_all(self, text: str) -> List[CategoryMatch]:
        """提取所有物料類別"""
        results = []

        for keyword in sorted(self._keyword_to_category.keys(), key=len, reverse=True):
            if keyword in text:
                # _keyword_to_category[keyword] 返回 (category_code, priority)
                category_code = self._keyword_to_category[keyword][0]
                category_name = self._get_category_name(category_code)
                results.append(
                    CategoryMatch(
                        category_code=category_code,
                        category_name=category_name,
                        matched_keyword=keyword,
                        confidence=1.0,
                    )
                )

        return results

    def get_all_rules(self) -> Dict[str, List[str]]:
        """獲取所有規則（用於測試）"""
        rules = {}
        for keyword, (category_code, priority) in self._keyword_to_category.items():
            if category_code not in rules:
                rules[category_code] = []
            if keyword not in rules[category_code]:
                rules[category_code].append(keyword)
        return rules

    def get_categories(self) -> List[str]:
        """獲取所有類別代碼"""
        return list(set(category for category, _ in self._keyword_to_category.values()))


# 便捷函數
def extract_category(text: str) -> Optional[CategoryMatch]:
    """便捷函數：提取物料類別"""
    extractor = MaterialCategoryExtractor()
    return extractor.extract(text)


def extract_category_as_dict(text: str) -> Dict[str, Any]:
    """便捷函數：提取物料類別並轉為字典"""
    extractor = MaterialCategoryExtractor()
    match = extractor.extract(text)
    if match:
        return {
            "category_code": match.category_code,
            "category_name": match.category_name,
        }
    return {}


if __name__ == "__main__":
    extractor = MaterialCategoryExtractor()

    print("=" * 80)
    print("MaterialCategoryExtractor 測試")
    print("=" * 80)

    test_cases = [
        # 基礎類別
        ("原料庫存", "RAW"),
        ("原材料採購", "RAW"),
        ("半成品入庫", "SEMI_FINISHED"),
        ("成品出貨", "FINISHED"),
        ("包裝材料報價", "PACKAGING"),
        ("耗材使用", "CONSUMABLE"),
        ("備品庫存", "SPARE_PART"),
        ("輔料消耗", "SUBMATERIAL"),
        # 材質類別
        ("塑料件報價", "PLASTIC"),
        ("金屬零件", "METAL"),
        ("電子元件", "ELECTRONIC"),
        ("化學品管理", "CHEMICAL"),
        ("紙箱包裝", "PAPER"),
        ("布料採購", "TEXTILE"),
        # ABC 分類
        ("A類物料盤點", "A_CLASS"),
        ("B類物料庫存", "B_CLASS"),
        ("C類物料管理", "C_CLASS"),
        # 採購分類
        ("mro 物料", "MRO"),
        ("直接原料", "RAW_DIRECT"),
        ("間接物料", "INDIRECT"),
        # 模糊表達
        ("這類物料", None),
        ("那個類別", None),
    ]

    print(f"\n{'輸入':<20} | {'識別結果':<15} | {'類別名稱':<10}")
    print("-" * 50)

    for text, expected in test_cases:
        result = extractor.extract(text)
        if result:
            status = "✅" if result.category_code == expected else "❌"
            print(f"{text:<20} | {result.category_code:<15} | {result.category_name:<10} {status}")
        else:
            # 檢查模糊表達
            clarification = extractor.check_fuzzy(text)
            if clarification.need_clarification:
                print(
                    f"{text:<20} | {'Clarification':<15} | 需要澄清 {clarification.fuzzy_keyword}"
                )
            else:
                print(f"{text:<20} | {'None':<15} | {'-':<10} ❌")

    print("\n" + "=" * 80)
    print("所有類別代碼:")
    for cat in extractor.get_categories():
        print(f"  - {cat}: {extractor._get_category_name(cat)}")
    print("=" * 80)
