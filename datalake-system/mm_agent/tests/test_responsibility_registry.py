# 代碼功能說明: P-T-A-O 職責分派 Registry 測試套件
# 創建日期: 2026-03-10
# 創建人: Daniel Chung
# 最後修改日期: 2026-03-10

"""
P-T-A-O 職責分派 Registry 單元測試

測試 ResponsibilityRegistry 的核心功能：
- handler 註冊與取得
- 已知/未知類型判斷
- 動態管理職責類型
"""

import pytest
from typing import Dict, Any
from mm_agent.ptao.responsibility_registry import ResponsibilityRegistry


@pytest.fixture
def registry():
    """創建空 registry 實例"""
    return ResponsibilityRegistry()


@pytest.fixture
def sample_handlers():
    """定義範例 handler 函數"""

    async def handler_query_part(params: Dict[str, Any]) -> Dict[str, Any]:
        """模擬查詢料號 handler"""
        return {"part_number": params.get("part_number")}

    async def handler_query_stock(params: Dict[str, Any]) -> Dict[str, Any]:
        """模擬查詢庫存 handler"""
        return {"quantity": params.get("quantity")}

    async def handler_analyze_shortage(params: Dict[str, Any]) -> Dict[str, Any]:
        """模擬分析缺料 handler"""
        return {"shortage": params.get("quantity") - params.get("available", 0)}

    return {
        "query_part": handler_query_part,
        "query_stock": handler_query_stock,
        "analyze_shortage": handler_analyze_shortage,
    }


class TestResponsibilityRegistry:
    """ResponsibilityRegistry 測試套件"""

    def test_register_and_get_handler(self, registry, sample_handlers):
        """
        測試：註冊 handler 並成功取得

        驗證：
        - register() 不拋出異常
        - get_handler() 能取得已註冊的 handler
        """
        handler = sample_handlers["query_part"]
        registry.register("query_part", handler)

        retrieved = registry.get_handler("query_part")
        assert retrieved is not None
        assert retrieved is handler

    def test_get_unknown_type_returns_none(self, registry):
        """
        測試：未知類型返回 None（不拋出異常）

        驗證：
        - get_handler() 對未知類型返回 None（友善失敗）
        - 不拋出異常
        """
        result = registry.get_handler("unknown_responsibility_type")
        assert result is None

    def test_has_handler_true(self, registry, sample_handlers):
        """
        測試：已註冊類型 has_handler 返回 True

        驗證：
        - has_handler() 對已註冊類型返回 True
        """
        handler = sample_handlers["query_stock"]
        registry.register("query_stock", handler)

        assert registry.has_handler("query_stock") is True

    def test_has_handler_false(self, registry):
        """
        測試：未知類型 has_handler 返回 False

        驗證：
        - has_handler() 對未知類型返回 False
        """
        assert registry.has_handler("unknown_type") is False

    def test_list_types(self, registry, sample_handlers):
        """
        測試：list_types() 返回所有已註冊類型

        驗證：
        - list_types() 返回已註冊的所有類型
        - 順序可能不一致（依賴 dict 迭代）
        """
        registry.register("query_part", sample_handlers["query_part"])
        registry.register("query_stock", sample_handlers["query_stock"])
        registry.register("analyze_shortage", sample_handlers["analyze_shortage"])

        types_list = registry.list_types()
        assert len(types_list) == 3
        assert "query_part" in types_list
        assert "query_stock" in types_list
        assert "analyze_shortage" in types_list

    def test_overwrite_handler(self, registry, sample_handlers):
        """
        測試：重新 register 同一類型不報錯

        驗證：
        - 第二次 register 同一類型覆蓋前一個 handler
        - 不拋出異常
        """
        handler1 = sample_handlers["query_part"]
        handler2 = sample_handlers["query_stock"]

        registry.register("query_part", handler1)
        assert registry.get_handler("query_part") is handler1

        # 覆蓋前一個 handler
        registry.register("query_part", handler2)
        assert registry.get_handler("query_part") is handler2

    def test_handler_is_callable(self, registry, sample_handlers):
        """
        測試：取得的 handler 可以被呼叫

        驗證：
        - 取得的 handler 是可呼叫的（callable）
        """
        handler = sample_handlers["query_part"]
        registry.register("query_part", handler)

        retrieved = registry.get_handler("query_part")
        assert callable(retrieved)

    def test_empty_registry(self, registry):
        """
        測試：空 registry 行為正確

        驗證：
        - 空 registry 的 list_types() 返回空列表
        - 空 registry 的 has_handler() 對任何類型返回 False
        - 空 registry 的 get_handler() 對任何類型返回 None
        """
        assert registry.list_types() == []
        assert registry.has_handler("any_type") is False
        assert registry.get_handler("any_type") is None

    def test_multiple_register_unregister_cycle(self, registry, sample_handlers):
        """
        測試：多次註冊/註銷循環

        驗證：
        - 支援動態註冊多個 handler
        - list_types() 正確反映當前狀態
        """
        # 第一輪：註冊 2 個
        registry.register("query_part", sample_handlers["query_part"])
        registry.register("query_stock", sample_handlers["query_stock"])
        assert len(registry.list_types()) == 2

        # 第二輪：註冊第 3 個
        registry.register("analyze_shortage", sample_handlers["analyze_shortage"])
        assert len(registry.list_types()) == 3

        # 驗證所有都能取得
        assert registry.has_handler("query_part") is True
        assert registry.has_handler("query_stock") is True
        assert registry.has_handler("analyze_shortage") is True

    def test_seven_default_types_support(self, registry, sample_handlers):
        """
        測試：Registry 預設支援 7 種類型（但不自動建立）

        驗證：
        - 7 種類型未被自動建立（empty registry）
        - 但可以被手動 register
        """
        # 驗證初始狀態：未被自動建立
        assert registry.has_handler("query_part") is False
        assert registry.has_handler("query_stock") is False
        assert registry.has_handler("query_stock_history") is False
        assert registry.has_handler("analyze_shortage") is False
        assert registry.has_handler("generate_purchase_order") is False
        assert registry.has_handler("analyze_existing_result") is False
        assert registry.has_handler("clarification_needed") is False

        # 驗證可以手動 register
        registry.register("query_part", sample_handlers["query_part"])
        assert registry.has_handler("query_part") is True
