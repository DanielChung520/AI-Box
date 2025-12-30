# 代碼功能說明: 緩存工具測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""緩存工具測試"""

from __future__ import annotations

import time

from tools.utils.cache import Cache, generate_cache_key, get_cache


class TestCache:
    """緩存類測試"""

    def test_set_and_get(self):
        """測試設置和獲取緩存"""
        cache = Cache()
        cache.set("test_key", "test_value", ttl=3600.0)

        value = cache.get("test_key")
        assert value == "test_value"

    def test_get_nonexistent_key(self):
        """測試獲取不存在的鍵"""
        cache = Cache()
        value = cache.get("nonexistent_key")

        assert value is None

    def test_cache_expiration(self):
        """測試緩存過期"""
        cache = Cache()
        cache.set("test_key", "test_value", ttl=0.1)  # 100ms TTL

        # 立即獲取應該有值
        assert cache.get("test_key") == "test_value"

        # 等待過期
        time.sleep(0.15)

        # 過期後應該返回 None
        assert cache.get("test_key") is None

    def test_delete_key(self):
        """測試刪除鍵"""
        cache = Cache()
        cache.set("test_key", "test_value")
        cache.delete("test_key")

        assert cache.get("test_key") is None

    def test_delete_nonexistent_key(self):
        """測試刪除不存在的鍵（不應該報錯）"""
        cache = Cache()
        cache.delete("nonexistent_key")  # 不應該報錯

    def test_clear_cache(self):
        """測試清空緩存"""
        cache = Cache()
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()

        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_different_value_types(self):
        """測試不同類型的值"""
        cache = Cache()

        # 字符串
        cache.set("str_key", "string_value")
        assert cache.get("str_key") == "string_value"

        # 數字
        cache.set("int_key", 123)
        assert cache.get("int_key") == 123

        # 列表
        cache.set("list_key", [1, 2, 3])
        assert cache.get("list_key") == [1, 2, 3]

        # 字典
        cache.set("dict_key", {"a": 1, "b": 2})
        assert cache.get("dict_key") == {"a": 1, "b": 2}

    def test_default_ttl(self):
        """測試默認 TTL"""
        cache = Cache()
        cache.set("test_key", "test_value")  # 使用默認 TTL (3600 秒)

        # 立即獲取應該有值
        assert cache.get("test_key") == "test_value"

    def test_expired_entry_removal(self):
        """測試過期條目自動移除"""
        cache = Cache()
        cache.set("test_key", "test_value", ttl=0.1)

        # 等待過期
        time.sleep(0.15)

        # 獲取應該返回 None，並且條目應該被移除
        assert cache.get("test_key") is None
        # 再次獲取也應該返回 None（條目已被移除）
        assert cache.get("test_key") is None


class TestGenerateCacheKey:
    """緩存鍵生成函數測試"""

    def test_generate_cache_key_with_prefix(self):
        """測試生成緩存鍵（帶前綴）"""
        key = generate_cache_key("test_prefix", param1="value1", param2="value2")

        assert key.startswith("test_prefix:")
        assert len(key) > len("test_prefix:")

    def test_generate_cache_key_consistency(self):
        """測試緩存鍵一致性（相同參數生成相同鍵）"""
        key1 = generate_cache_key("prefix", a=1, b=2)
        key2 = generate_cache_key("prefix", a=1, b=2)

        assert key1 == key2

    def test_generate_cache_key_order_independent(self):
        """測試緩存鍵參數順序無關"""
        key1 = generate_cache_key("prefix", a=1, b=2)
        key2 = generate_cache_key("prefix", b=2, a=1)

        assert key1 == key2

    def test_generate_cache_key_different_params(self):
        """測試不同參數生成不同鍵"""
        key1 = generate_cache_key("prefix", a=1, b=2)
        key2 = generate_cache_key("prefix", a=2, b=1)

        assert key1 != key2

    def test_generate_cache_key_no_params(self):
        """測試無參數生成鍵"""
        key = generate_cache_key("prefix")

        assert key.startswith("prefix:")
        assert len(key) > len("prefix:")


class TestGetCache:
    """獲取緩存實例函數測試"""

    def test_get_cache_singleton(self):
        """測試單例模式"""
        cache1 = get_cache()
        cache2 = get_cache()

        assert cache1 is cache2

    def test_get_cache_returns_cache_instance(self):
        """測試返回 Cache 實例"""
        cache = get_cache()

        assert isinstance(cache, Cache)
