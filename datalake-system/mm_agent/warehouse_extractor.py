# -*- coding: utf-8 -*-
# 代碼功能說明: 倉庫提取器
# 創建日期: 2026-02-06
# 創建人: AI-Box 開發團隊

"""WarehouseExtractor - 獨立倉庫提取模組

職責：
- 提取倉庫位置（原料倉、成品倉、各區域倉庫等）
- 支持企業級倉庫編碼
- 獨立模組，可測試，可移植

倉庫類型：
- RAW_WAREHOUSE: 原料倉
- FINISHED_WAREHOUSE: 成品倉
- SEMI_WAREHOUSE: 半成品倉
- PACKAGING_WAREHOUSE: 包裝材料倉
- CONSUMABLE_WAREHOUSE: 消耗品倉
- RETURN_WAREHOUSE: 退貨倉
- QUALITY_HOLD: 品質待驗區
- TRANSFER: 中轉區
"""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class WarehouseMatch:
    """倉庫匹配結果"""

    warehouse_code: str  # 倉庫代碼（如：W01, RAW01）
    warehouse_name: str  # 倉庫名稱（如：原料倉）
    matched_keyword: Optional[str] = None
    confidence: float = 1.0


@dataclass
class WarehouseClarification:
    """倉庫澄清結果（用於模糊表達）"""

    need_clarification: bool = False
    fuzzy_keyword: Optional[str] = None
    question: Optional[str] = None
    suggestions: List[str] = field(default_factory=list)


class WarehouseExtractor:
    """獨立倉庫提取器

    特點：
    - 純規則引擎，無 LLM 依賴
    - 支持簡體/繁體中文
    - 支持企業級倉庫編碼
    - 獨立模組，可測試，可移植
    - 可配置規則
    """

    # ========== 按功能分類 ==========

    # 原料相關倉庫
    RAW_WAREHOUSE = {
        "RAW01": [
            "原料倉",
            "原材料倉",
            "原料倉庫",
            "原材料倉庫",
            "原料區",
            "raw material warehouse",
            "raw warehouse",
            "原料庫",
            "原物料倉",
            "主原料倉",
        ],
        "RAW02": [
            "進料區",
            "來料區",
            "收料區",
            "進貨區",
            "incoming area",
            "receiving area",
            "收貨區",
        ],
        "RAW03": [
            "原料待驗區",
            "來料待驗區",
            "iqc區",
            "iqc區域",
            "進料檢驗區",
            "待驗原料區",
        ],
    }

    # 半成品相關倉庫
    SEMI_WAREHOUSE = {
        "SEMI01": [
            "半成品倉",
            "半製品倉",
            "半成品倉庫",
            "半製品倉庫",
            "半成品區",
            "wip warehouse",
            "wip區",
            "在製品倉",
            "生产中物料倉",
        ],
        "SEMI02": [
            "工藝品倉",
            "加工品倉",
            " intermediate",
            "中間品倉",
            "加工中物料區",
        ],
    }

    # 成品相關倉庫
    FINISHED_WAREHOUSE = {
        "FIN01": [
            "成品倉",
            "成品倉庫",
            "製成品倉",
            "成品區",
            "finished goods warehouse",
            "成品庫",
            "完工品倉",
            "完成品倉",
        ],
        "FIN02": [
            "成品待驗區",
            "完工待驗區",
            "oqc區",
            "oqc區域",
            "出貨檢驗區",
            "待出貨區",
        ],
        "FIN03": [
            "成品包裝區",
            "包裝區",
            "包裝成品區",
            "包裝線",
            "packing area",
        ],
    }

    # 包裝材料倉庫
    PACKAGING_WAREHOUSE = {
        "PKG01": [
            "包裝材料倉",
            "包裝倉",
            "包裝倉庫",
            "包材倉",
            "包裝區",
            "packaging warehouse",
            "包材區",
        ],
        "PKG02": [
            "紙箱倉",
            "紙盒倉",
            "紙製品倉",
            "紙張倉",
            "紙箱區",
            "紙盒區",
        ],
        "PKG03": [
            "塑膠袋倉",
            "膠袋倉",
            "塑料袋倉",
            "袋子倉",
            "包装袋區",
        ],
    }

    # 消耗品倉庫
    CONSUMABLE_WAREHOUSE = {
        "CON01": [
            "消耗品倉",
            "耗材倉",
            "消耗材料倉",
            "耗材區",
            "consumable warehouse",
            "用品倉",
        ],
        "CON02": [
            "潤滑油倉",
            "潤滑劑倉",
            "油品倉",
            "潤滑區",
            "lubricant warehouse",
        ],
        "CON03": [
            "工具倉",
            "工具區",
            "工裝倉",
            "夾具倉",
            "tool warehouse",
        ],
    }

    # 退貨/客退倉庫
    RETURN_WAREHOUSE = {
        "RET01": [
            "退貨倉",
            "退貨區",
            "客退區",
            "客戶退貨區",
            "return warehouse",
            "returns area",
            "退貨倉庫",
        ],
        "RET02": [
            "待處理退貨",
            "待判退貨",
            "退貨待判區",
            "退貨檢驗區",
            "returns inspection area",
        ],
    }

    # 品質相關區域
    QUALITY_HOLD = {
        "QA01": [
            "品質待驗區",
            "待驗區",
            "品質區",
            "qa area",
            "quality hold",
            "quality inspection area",
            "iqc區",
            "oqc區",
        ],
        "QA02": [
            "不合格品區",
            "ng區",
            "不良品區",
            "ng區域",
            "reject area",
            "defective area",
        ],
        "QA03": [
            "隔離區",
            " quarantine area",
            "hold area",
            "待隔離區",
        ],
    }

    # 中轉/暫存區域
    TRANSFER = {
        "TRN01": [
            "中轉區",
            " transit area",
            "轉運區",
            "暫存區",
            "temporary storage",
            "暫存區域",
        ],
        "TRN02": [
            "發貨區",
            "出貨區",
            "shipping area",
            " shipment area",
            "出貨準備區",
        ],
        "TRN03": [
            "收貨區",
            "收貨區域",
            "receiving area",
            "收货区",
        ],
    }

    # ========== 按位置分類 ==========

    # 廠區位置
    FACTORY_LOCATION = {
        "FAC01": [
            "一廠",
            "工廠一",
            "factory 1",
            "廠房一",
            "一廠區",
            "第一工廠",
        ],
        "FAC02": [
            "二廠",
            "工廠二",
            "factory 2",
            "廠房二",
            "二廠區",
            "第二工廠",
        ],
        "FAC03": [
            "三廠",
            "工廠三",
            "factory 3",
            "廠房三",
            "三廠區",
            "第三工廠",
        ],
    }

    # 樓層位置
    FLOOR_LOCATION = {
        "FLR01": [
            "一樓",
            "一層",
            "地面層",
            "ground floor",
            "首層",
            "一楼",
            "首層",
        ],
        "FLR02": [
            "二樓",
            "二層",
            "second floor",
            "二層樓",
            "二楼",
        ],
        "FLR03": [
            "三樓",
            "三層",
            "third floor",
            "三層樓",
            "三楼",
        ],
        "FLR_B1": [
            "地下一樓",
            "地下室",
            "basement",
            "b1",
            "負一層",
            "地下層",
        ],
    }

    # 區域位置
    ZONE_LOCATION = {
        "ZONE_A": ["a區", "A區", "a區域", "A區域", "zone a"],
        "ZONE_B": ["b區", "B區", "b區域", "B區域", "zone b"],
        "ZONE_C": ["c區", "C區", "c區域", "C區域", "zone c"],
        "ZONE_D": ["d區", "D區", "d區域", "D區域", "zone d"],
    }

    # ========== 特殊倉庫 ==========

    # 危險品倉庫
    HAZARDOUS = {
        "HAZ01": [
            "危險品倉",
            "危險品倉庫",
            "危險品區",
            "hazardous material warehouse",
            "危險品存放區",
            "化學品倉",
            "溶劑倉",
        ]
    }

    # 冷鏈倉庫
    COLD_CHAIN = {
        "COLD01": [
            "冷藏倉",
            "冷藏區",
            " refrigerator",
            "cold storage",
            "冷庫",
            "冷冻倉",
        ],
        "COLD02": [
            "冷凍倉",
            "冷冻區",
            " freezer",
            "深冷區",
        ],
    }

    # ========== 模糊表達（需要 Clarification） ==========

    FUZZY_EXPRESSIONS = {
        "fuzzy_warehouse": ["倉庫", "倉", "庫", "庫房"],
        "fuzzy_location": ["那邊", "這邊", "那裡", "這裡"],
        "fuzzy_area": ["那個區", "這個區", "某個區"],
    }

    def __init__(self, custom_rules: Optional[Dict[str, List[str]]] = None):
        """初始化倉庫提取器

        Args:
            custom_rules: 自定義規則（可覆蓋預設規則）
        """
        # 按優先級順序定義（索引越大優先級越高）
        # 優先級從低到高
        priority_order = [
            (self.RAW_WAREHOUSE, 1),  # 原料倉庫
            (self.SEMI_WAREHOUSE, 2),  # 半成品倉庫
            (self.FINISHED_WAREHOUSE, 3),  # 成品倉庫
            (self.PACKAGING_WAREHOUSE, 4),  # 包裝材料倉庫
            (self.CONSUMABLE_WAREHOUSE, 5),  # 消耗品倉庫
            (self.RETURN_WAREHOUSE, 6),  # 退貨倉庫
            (self.QUALITY_HOLD, 7),  # 品質區域
            (self.TRANSFER, 8),  # 中轉區域
            (self.HAZARDOUS, 9),  # 危險品倉庫
            (self.COLD_CHAIN, 10),  # 冷鏈倉庫
            (self.FACTORY_LOCATION, 11),  # 廠區位置
            (self.FLOOR_LOCATION, 12),  # 樓層位置
            (self.ZONE_LOCATION, 13),  # 區域位置
        ]

        # 反向映射：關鍵詞 -> (倉庫代碼, 優先級)
        self._keyword_to_warehouse = {}

        for category_dict, priority in priority_order:
            for warehouse_code, keywords in category_dict.items():
                for keyword in keywords:
                    # 只有當關鍵詞不存在或優先級更高时才更新
                    if keyword not in self._keyword_to_warehouse:
                        self._keyword_to_warehouse[keyword] = (warehouse_code, priority)
                    elif self._keyword_to_warehouse[keyword][1] < priority:
                        self._keyword_to_warehouse[keyword] = (warehouse_code, priority)

        # 如果有自定義規則，給予最高優先級
        if custom_rules:
            for warehouse_code, keywords in custom_rules.items():
                for keyword in keywords:
                    self._keyword_to_warehouse[keyword] = (warehouse_code, 100)

        # 模糊表達
        self.FUZZY_KEYWORDS = []
        for keywords in self.FUZZY_EXPRESSIONS.values():
            self.FUZZY_KEYWORDS.extend(keywords)

    def _get_clarification_question(self, fuzzy_type: str) -> tuple:
        """獲取澄清問題和建議"""
        questions = {
            "fuzzy_warehouse": (
                "請問具體是哪個倉庫？",
                ["原料倉", "成品倉", "半成品倉", "包裝材料倉", "退貨倉"],
            ),
            "fuzzy_location": (
                "請問具體位置是？",
                ["一廠/二廠", "一樓/二樓", "A區/B區/C區"],
            ),
            "fuzzy_area": (
                "請問具體是哪個區域？",
                ["原料區", "成品區", "待驗區", "中轉區"],
            ),
        }
        return questions.get(fuzzy_type, ("請提供具體倉庫位置", []))

    def extract(self, text: str) -> Optional[WarehouseMatch]:
        """提取倉庫

        Args:
            text: 用戶輸入文本

        Returns:
            WarehouseMatch 或 None
        """
        # 步驟 1：精確匹配（按關鍵詞長度排序，長的在前）
        sorted_keywords = sorted(
            self._keyword_to_warehouse.keys(),
            key=len,
            reverse=True,
        )

        for keyword in sorted_keywords:
            if keyword in text:
                # _keyword_to_warehouse[keyword] 返回 (warehouse_code, priority)
                warehouse_code = self._keyword_to_warehouse[keyword][0]
                warehouse_name = self._get_warehouse_name(warehouse_code)
                return WarehouseMatch(
                    warehouse_code=warehouse_code,
                    warehouse_name=warehouse_name,
                    matched_keyword=keyword,
                    confidence=1.0,
                )

        # 步驟 2：嘗試匹配倉庫編碼（如 W01, W02, A區）
        warehouse_code_match = self._extract_warehouse_code(text)
        if warehouse_code_match:
            return warehouse_code_match

        return None

    def _extract_warehouse_code(self, text: str) -> Optional[WarehouseMatch]:
        """提取倉庫編碼"""
        # W01, W02, W03 等
        pattern = r"\bW(\d{2})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            code = f"W{match.group(1)}"
            return WarehouseMatch(
                warehouse_code=code,
                warehouse_name=f"倉庫{code}",
                matched_keyword=match.group(0),
                confidence=0.9,
            )

        # RAW01, RAW02, FIN01 等
        pattern = r"\b(RAW|SEMI|FIN|PKG|CON|RET|QA|TRN|HAZ|COLD)(\d{2})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            code = f"{match.group(1).upper()}{match.group(2)}"
            return WarehouseMatch(
                warehouse_code=code,
                warehouse_name=self._get_warehouse_name(code),
                matched_keyword=match.group(0),
                confidence=0.9,
            )

        return None

    def _get_warehouse_name(self, warehouse_code: str) -> str:
        """獲取倉庫名稱"""
        warehouse_names = {
            # 原料倉
            "RAW01": "原料倉",
            "RAW02": "進料區",
            "RAW03": "原料待驗區",
            # 半成品倉
            "SEMI01": "半成品倉",
            "SEMI02": "工藝品倉",
            # 成品倉
            "FIN01": "成品倉",
            "FIN02": "成品待驗區",
            "FIN03": "成品包裝區",
            # 包裝材料倉
            "PKG01": "包裝材料倉",
            "PKG02": "紙箱倉",
            "PKG03": "塑膠袋倉",
            # 消耗品倉
            "CON01": "消耗品倉",
            "CON02": "潤滑油倉",
            "CON03": "工具倉",
            # 退貨倉
            "RET01": "退貨倉",
            "RET02": "待處理退貨",
            # 品質區域
            "QA01": "品質待驗區",
            "QA02": "不合格品區",
            "QA03": "隔離區",
            # 中轉區域
            "TRN01": "中轉區",
            "TRN02": "發貨區",
            "TRN03": "收貨區",
            # 廠區位置
            "FAC01": "一廠",
            "FAC02": "二廠",
            "FAC03": "三廠",
            # 樓層位置
            "FLR01": "一樓",
            "FLR02": "二樓",
            "FLR03": "三樓",
            "FLR_B1": "地下室",
            # 區域位置
            "ZONE_A": "A區",
            "ZONE_B": "B區",
            "ZONE_C": "C區",
            "ZONE_D": "D區",
            # 特殊倉庫
            "HAZ01": "危險品倉",
            "COLD01": "冷藏倉",
            "COLD02": "冷凍倉",
        }
        return warehouse_names.get(warehouse_code, warehouse_code)

    def check_fuzzy(self, text: str) -> WarehouseClarification:
        """檢查模糊表達（返回 Clarification）"""
        for fuzzy_type, keywords in self.FUZZY_EXPRESSIONS.items():
            for keyword in keywords:
                if keyword in text:
                    question, suggestions = self._get_clarification_question(fuzzy_type)
                    return WarehouseClarification(
                        need_clarification=True,
                        fuzzy_keyword=keyword,
                        question=question,
                        suggestions=suggestions,
                    )
        return WarehouseClarification(need_clarification=False)

    def extract_with_clarification(self, text: str) -> tuple:
        """提取倉庫（包含 Clarification）

        Returns:
            tuple: (WarehouseMatch or None, WarehouseClarification)
        """
        # 先檢查模糊表達
        clarification = self.check_fuzzy(text)
        if clarification.need_clarification:
            return None, clarification

        # 提取精確倉庫
        match = self.extract(text)
        return match, WarehouseClarification(need_clarification=False)

    def extract_all(self, text: str) -> List[WarehouseMatch]:
        """提取所有倉庫"""
        results = []

        # 按關鍵詞長度排序
        for keyword in sorted(self._keyword_to_warehouse.keys(), key=len, reverse=True):
            if keyword in text:
                # _keyword_to_warehouse[keyword] 返回 (warehouse_code, priority)
                warehouse_code = self._keyword_to_warehouse[keyword][0]
                warehouse_name = self._get_warehouse_name(warehouse_code)
                results.append(
                    WarehouseMatch(
                        warehouse_code=warehouse_code,
                        warehouse_name=warehouse_name,
                        matched_keyword=keyword,
                        confidence=1.0,
                    )
                )

        return results

    def get_all_rules(self) -> Dict[str, List[str]]:
        """獲取所有規則（用於測試）"""
        rules = {}
        for keyword, (warehouse_code, priority) in self._keyword_to_warehouse.items():
            if warehouse_code not in rules:
                rules[warehouse_code] = []
            if keyword not in rules[warehouse_code]:
                rules[warehouse_code].append(keyword)
        return rules

    def get_warehouses(self) -> List[str]:
        """獲取所有倉庫代碼"""
        return list(set(warehouse for warehouse, _ in self._keyword_to_warehouse.values()))


# 便捷函數
def extract_warehouse(text: str) -> Optional[WarehouseMatch]:
    """便捷函數：提取倉庫"""
    extractor = WarehouseExtractor()
    return extractor.extract(text)


def extract_warehouse_as_dict(text: str) -> Dict[str, Any]:
    """便捷函數：提取倉庫並轉為字典"""
    extractor = WarehouseExtractor()
    match = extractor.extract(text)
    if match:
        return {
            "warehouse_code": match.warehouse_code,
            "warehouse_name": match.warehouse_name,
        }
    return {}


if __name__ == "__main__":
    extractor = WarehouseExtractor()

    print("=" * 80)
    print("WarehouseExtractor 測試")
    print("=" * 80)

    test_cases = [
        # 原料倉
        ("原料倉庫存", "RAW01"),
        ("原材料倉庫", "RAW01"),
        ("進料區收貨", "RAW02"),
        ("原料待驗區", "RAW03"),
        # 半成品倉
        ("半成品倉出庫", "SEMI01"),
        ("wip區物料", "SEMI01"),
        # 成品倉
        ("成品倉出貨", "FIN01"),
        ("成品待驗區", "FIN02"),
        ("成品包裝區", "FIN03"),
        # 包裝材料倉
        ("包裝材料倉領料", "PKG01"),
        ("紙箱倉存儲", "PKG02"),
        ("塑膠袋倉", "PKG03"),
        # 消耗品倉
        ("消耗品倉", "CON01"),
        ("工具倉借用", "CON03"),
        # 退貨倉
        ("退貨倉處理", "RET01"),
        ("待處理退貨", "RET02"),
        # 品質區域
        ("品質待驗區", "QA01"),
        ("不合格品區", "QA02"),
        ("ng區", "QA02"),
        ("隔離區存放", "QA03"),
        # 中轉區
        ("中轉區暫存", "TRN01"),
        ("發貨區備貨", "TRN02"),
        ("收貨區入庫", "TRN03"),
        # 位置信息
        ("一廠原料倉", "FAC01"),
        ("二樓成品倉", "FLR02"),
        ("A區庫存", "ZONE_A"),
        # 倉庫編碼
        ("W01 倉庫", "W01"),
        ("RAW02 區域", "RAW02"),
        ("FIN01 出庫", "FIN01"),
        # 特殊倉庫
        ("危險品倉", "HAZ01"),
        ("冷藏倉", "COLD01"),
        ("冷庫溫度", "COLD01"),
        # 模糊表達
        ("倉庫在那邊", None),
        ("這邊的庫存", None),
        ("那個區的物料", None),
    ]

    print(f"\n{'輸入':<20} | {'識別結果':<12} | {'倉庫名稱':<10}")
    print("-" * 50)

    for text, expected in test_cases:
        result = extractor.extract(text)
        if result:
            status = "✅" if result.warehouse_code == expected else "❌"
            print(
                f"{text:<20} | {result.warehouse_code:<12} | {result.warehouse_name:<10} {status}"
            )
        else:
            # 檢查模糊表達
            clarification = extractor.check_fuzzy(text)
            if clarification.need_clarification:
                print(
                    f"{text:<20} | {'Clarification':<12} | 需要澄清 {clarification.fuzzy_keyword}"
                )
            else:
                print(f"{text:<20} | {'None':<12} | {'-':<10} ❌")

    print("\n" + "=" * 80)
    print("所有倉庫代碼:")
    for cat in extractor.get_warehouses():
        print(f"  - {cat}: {extractor._get_warehouse_name(cat)}")
    print("=" * 80)
