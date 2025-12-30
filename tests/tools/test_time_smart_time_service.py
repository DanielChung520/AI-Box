# 代碼功能說明: 時間服務測試
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""時間服務測試"""

from __future__ import annotations

import time
from datetime import datetime

from tools.time.smart_time_service import TimeService, get_time_service


class TestTimeService:
    """時間服務測試"""

    def test_initialization(self):
        """測試初始化"""
        service = TimeService(cache_duration=0.1)
        assert service._cache_duration == 0.1
        assert service._cached_time > 0
        assert service._last_update > 0

    def test_now_returns_timestamp(self):
        """測試 now() 返回時間戳"""
        service = TimeService()
        timestamp = service.now()

        assert isinstance(timestamp, float)
        assert timestamp > 0
        assert timestamp > time.time() - 1  # 應該是當前時間附近

    def test_now_datetime_returns_datetime(self):
        """測試 now_datetime() 返回 datetime 對象"""
        service = TimeService()
        dt = service.now_datetime()

        assert isinstance(dt, datetime)
        assert dt.year > 2020  # 應該是合理的年份

    def test_now_utc_datetime_returns_utc_datetime(self):
        """測試 now_utc_datetime() 返回 UTC datetime 對象"""
        service = TimeService()
        dt = service.now_utc_datetime()

        assert isinstance(dt, datetime)
        assert dt.year > 2020

    def test_cache_mechanism(self):
        """測試緩存機制"""
        service = TimeService(cache_duration=0.2)  # 200ms 緩存

        # 第一次調用
        timestamp1 = service.now()
        time.sleep(0.05)  # 等待 50ms（小於緩存時間）

        # 第二次調用（應該使用緩存）
        timestamp2 = service.now()

        # 時間應該增加約 50ms
        assert timestamp2 > timestamp1
        assert timestamp2 - timestamp1 < 0.1  # 應該接近 50ms

    def test_cache_refresh(self):
        """測試緩存刷新"""
        service = TimeService(cache_duration=0.1)  # 100ms 緩存

        # 第一次調用
        timestamp1 = service.now()
        time.sleep(0.15)  # 等待 150ms（超過緩存時間）

        # 第二次調用（應該刷新緩存）
        timestamp2 = service.now()

        # 時間應該增加約 150ms
        assert timestamp2 > timestamp1
        assert timestamp2 - timestamp1 >= 0.1  # 應該接近 150ms

    def test_thread_safety(self):
        """測試線程安全性"""
        import threading

        service = TimeService()
        results = []

        def get_time():
            results.append(service.now())

        threads = [threading.Thread(target=get_time) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有線程都應該成功獲取時間
        assert len(results) == 10
        assert all(isinstance(r, float) and r > 0 for r in results)

    def test_custom_cache_duration(self):
        """測試自定義緩存持續時間"""
        service = TimeService(cache_duration=0.5)  # 500ms 緩存
        assert service._cache_duration == 0.5

    def test_singleton_pattern(self):
        """測試單例模式"""
        service1 = get_time_service()
        service2 = get_time_service()

        assert service1 is service2

    def test_get_smart_time_service_alias(self):
        """測試向後兼容別名"""
        from tools.time.smart_time_service import get_smart_time_service

        service1 = get_time_service()
        service2 = get_smart_time_service()

        assert service1 is service2

    def test_time_accuracy(self):
        """測試時間精度"""
        service = TimeService(cache_duration=0.1)

        # 連續調用應該返回遞增的時間戳
        timestamps = [service.now() for _ in range(5)]
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1]

    def test_perf_counter_usage(self):
        """測試使用 perf_counter 計算經過的時間"""
        service = TimeService(cache_duration=0.2)

        # 獲取初始時間
        initial_time = service.now()
        time.sleep(0.05)  # 等待 50ms

        # 再次獲取時間（應該使用 perf_counter 計算）
        current_time = service.now()

        # 時間差應該接近 50ms
        time_diff = current_time - initial_time
        assert 0.04 < time_diff < 0.06  # 允許一些誤差
