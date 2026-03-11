# -*- coding: utf-8 -*-
"""
代碼功能說明: detect_query_complexity() 複雜度判斷真值表測試
創建日期: 2026-03-11
創建人: Daniel Chung
最後修改日期: 2026-03-11
"""

import pytest

from data_agent.services.schema_driven_query.da_intent_rag import (
    detect_query_complexity,
    COMPLEX_QUERY_KEYWORDS,
)


class TestDetectQueryComplexity:
    """
    detect_query_complexity() 單元測試

    測試覆蓋：
    1. 簡單查詢（無複雜關鍵詞）
    2. 複雜查詢（含複雜關鍵詞）
    3. 邊界情況（包含時間詞彙、排序詞彙等）
    """

    # ──────────────────────────────────────────────────
    # SIMPLE 查詢（不應觸發複雜度檢測）
    # ──────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "query,expected_complexity",
        [
            # 基本查詢
            ("查詢料號 NI001 的庫存", "simple"),
            ("查詢工單 SF001 的狀態", "simple"),
            ("列出倉庫 A01 的所有料件", "simple"),
            ("查詢商品詳情", "simple"),
            # 簡單篩選
            ("查詢倉庫 A01 的庫存", "simple"),
            ("篩選規格為 M8 的產品", "simple"),
            ("查詢商品代碼 NI001", "simple"),
            # 簡單統計（單一結果）
            ("查詢今天的出貨數量", "simple"),
            ("查詢本月接單量", "simple"),
            ("查詢去年 11 月的訂單", "simple"),
            # 無複雜關鍵詞的查詢
            ("有哪些商品", "simple"),
            ("商品列表", "simple"),
            ("列出所有工單", "simple"),
        ],
        ids=[
            "basic_inventory_query",
            "basic_workorder_query",
            "basic_warehouse_list",
            "basic_product_detail",
            "warehouse_filter",
            "spec_filter",
            "product_code_query",
            "temporal_today",
            "temporal_thismonth",
            "temporal_lastyear",
            "open_query_1",
            "open_query_2",
            "open_query_3",
        ],
    )
    def test_simple_queries(self, query: str, expected_complexity: str):
        """簡單查詢應返回 'simple'"""
        result = detect_query_complexity(query)
        assert result == expected_complexity, f"Query: {query}"

    # ──────────────────────────────────────────────────
    # COMPLEX 查詢（應觸發複雜度檢測）
    # ──────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "query,expected_complexity,reason",
        [
            # Top-N 排名
            ("各倉庫庫存數量前 10 名排名", "complex", "前 + 排名"),
            ("庫存最多的前 5 個料號", "complex", "最多 + 前"),
            ("前 5 大客戶出貨量", "complex", "前 + 大"),
            # 極值操作
            ("庫存最低的料號", "complex", "最低"),
            ("銷量最高的產品", "complex", "最高"),
            ("出貨最少的工單", "complex", "最少"),
            ("庫存最大的倉庫", "complex", "最大"),
            # 排序操作
            ("按庫存量排序", "complex", "排序"),
            ("依交期排序所有工單", "complex", "排序"),
            # 聚合統計
            ("本月出貨總計", "complex", "總計"),
            ("各工站的合計產出", "complex", "合計"),
            ("每週的小計", "complex", "小計"),
            # 計算比率
            ("各客戶出貨佔比", "complex", "佔比"),
            ("各品類銷售比例", "complex", "比例"),
            ("市場佔有百分比", "complex", "百分比"),
            # 比較操作
            ("比較 A 倉和 B 倉的庫存", "complex", "比較"),
            ("對比今年與去年出貨量", "complex", "對比"),
            # 複雜計算
            ("各工作站的產出排序", "complex", "排序"),
            ("品質良率排名", "complex", "排名（含 名 字）"),
            ("銷售額排序統計", "complex", "排序"),
            # 統計/趨勢/分析
            ("統計上個月各刀庫庫存總量", "complex", "統計"), 
            ("統計每個刀庫過去三個月的庫存總量並按刀庫分組", "complex", "統計 + 月度 + 分組"),
            ("各工廠月度出貨量趨勢分析", "complex", "月度 + 趨勢 + 分析"),
            ("每月出貨量統計", "complex", "統計"),
            ("過去一年的庫存趨勢", "complex", "趨勢"),
            ("年度出貨初管理", "complex", "年度"),
            ("季度預算統計", "complex", "季度 + 統計"),
        ],
        ids=[
            "topn_warehouse_inventory",
            "topn_stock_most",
            "topn_customer_shipping",
            "extremal_stock_lowest",
            "extremal_sales_highest",
            "extremal_shipping_least",
            "extremal_stock_largest",
            "sort_by_inventory",
            "sort_by_due_date",
            "agg_monthly_total",
            "agg_workstation_sum",
            "agg_weekly_subtotal",
            "ratio_customer_ratio",
            "ratio_category_percent",
            "ratio_market_share",
            "compare_warehouses",
            "compare_yearly",
            "agg_sort_output",
            "agg_quality_rank",
            "agg_sales_sort",
            "agg_monthly_prev_warehouse",
            "agg_monthly_by_warehouse",
            "agg_factory_monthly_trend",
            "agg_monthly_shipping",
            "agg_yearly_inventory_trend",
            "agg_annual_shipping_management",
            "agg_quarterly_budget",
        ],
    )
    def test_complex_queries(self, query: str, expected_complexity: str, reason: str):
        """複雜查詢應返回 'complex'"""
        result = detect_query_complexity(query)
        assert result == expected_complexity, f"Query: {query} (Reason: {reason})"

    # ──────────────────────────────────────────────────
    # 邊界情況：包含 "前" 的查詢（已知 Bug）
    # 這些測試目前會失敗，因為 "前" 被錯誤地分類為複雜關鍵詞
    # Task 6 將實現 context-aware regex 修復此問題
    # ──────────────────────────────────────────────────

    @pytest.mark.parametrize(
        "query,expected_complexity",
        [
            # 分頁操作（"前" 表示 "top N"，但無排序意圖）
            ("查詢料號 NI001 的庫存明細，前 10 筆", "simple"),
            # 時間詞彙（"前" 表示 "before/prior"）
            ("前天的出貨記錄", "simple"),
            ("以前的訂單記錄", "simple"),
            ("前月出貨數量", "simple"),
            # 位置詞彙（"前" 表示 "front/forward"）
            ("最前面的記錄", "simple"),
            ("最前面的料號", "simple"),
        ],
        ids=[
            "pagination_top_10",
            "temporal_before_day",
            "temporal_before_general",
            "temporal_before_month",
            "positional_frontmost",
            "positional_frontmost_item",
        ],
    )
    def test_queries_with_qian_contextual_bug(self, query: str, expected_complexity: str):
        """
        包含 "前" 字的查詢存在已知 Bug

        背景：COMPLEX_QUERY_KEYWORDS 包含 "前" 作為平文本匹配，導致：
        - "前天", "前月" 等時間詞被誤分為複雜
        - "前 10 筆" 等分頁操作被誤分為複雜

        修復：Task 6 將實現上下文感知的正則表達式，區別：
        - "前" 在 "Top-N 排名" 場景（複雜）
        - "前" 在時間/位置場景（簡單）

        預期行為（修復後）：
        - "查詢料號...前 10 筆" → simple（分頁）
        - "前天的出貨記錄" → simple（時間）
        - "庫存最多的前 5 名" → complex（Top-N 排名）
        """
        result = detect_query_complexity(query)
        assert result == expected_complexity, f"Query: {query}"


class TestComplexKeywordsList:
    """測試 COMPLEX_QUERY_KEYWORDS 列表的內容"""

    def test_keywords_contain_expected_values(self):
        """應包含所有預期的複雜查詢關鍵詞"""
        expected_keywords = [
            "最大",
            "最多",
            "最少",
            "最低",
            "最高",
            "排序",
            "名",
            "佔比",
            "比例",
            "百分比",
            "比較",
            "對比",
            "總計",
            "合計",
            "小計",
            "統計",
            "趨勢",
            "分析",
            "月度",
            "年度",
            "季度",
            "彙總",
            "匯總",
            "平均",
            "排名",
        ]
        for keyword in expected_keywords:
            assert keyword in COMPLEX_QUERY_KEYWORDS, f"Missing keyword: {keyword}"

    def test_keywords_are_strings(self):
        """所有關鍵詞應為字串"""
        for keyword in COMPLEX_QUERY_KEYWORDS:
            assert isinstance(keyword, str), f"Keyword {keyword} is not a string"

    def test_keywords_not_empty(self):
        """關鍵詞列表不應為空"""
        assert len(COMPLEX_QUERY_KEYWORDS) > 0, "COMPLEX_QUERY_KEYWORDS is empty"


class TestDetectQueryComplexityEdgeCases:
    """邊界情況測試"""

    def test_empty_query(self):
        """空查詢應返回 'simple'"""
        result = detect_query_complexity("")
        assert result == "simple"

    def test_whitespace_only_query(self):
        """只有空白的查詢應返回 'simple'"""
        result = detect_query_complexity("   ")
        assert result == "simple"

    def test_case_sensitivity(self):
        """測試大小寫敏感性（中文無大小寫）"""
        query = "查詢料號 NI001 的庫存"
        result = detect_query_complexity(query)
        assert result == "simple"

    def test_keyword_at_different_positions(self):
        """複雜關鍵詞在不同位置都應被檢測"""
        # 開頭
        result1 = detect_query_complexity("最多的料號是什麼")
        assert result1 == "complex"

        # 中間
        result2 = detect_query_complexity("查詢最多的料號")
        assert result2 == "complex"

        # 結尾
        result3 = detect_query_complexity("庫存排序")
        assert result3 == "complex"

    def test_multiple_keywords_in_query(self):
        """含多個複雜關鍵詞的查詢應返回 'complex'"""
        result = detect_query_complexity("按庫存量排序後的前 10 名料號")
        assert result == "complex"

    def test_keyword_as_substring(self):
        """關鍵詞作為子串也應被檢測"""
        # "最高" 包含 "最"
        query_with_max = "銷量最高的"
        result = detect_query_complexity(query_with_max)
        assert result == "complex"

        # "對比" 包含 "比"
        query_with_compare = "對比數據"
        result = detect_query_complexity(query_with_compare)
        assert result == "complex"
