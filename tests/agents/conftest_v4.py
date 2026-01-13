# 代碼功能說明: pytest 配置文件 - 用於保存 v4 測試結果
# 創建日期: 2026-01-12
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-12

"""pytest 配置 - 用於在測試完成後保存 v4 測試結果"""

import pytest
from pathlib import Path


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    """在所有測試完成後保存測試結果"""
    try:
        # 嘗試從測試模塊導入測試結果和保存函數
        from tests.agents.test_file_editing_agent_routing_v4 import (
            _test_results,
            save_test_results,
        )

        if _test_results:
            output_file = save_test_results()
            print(f"\n{'='*80}")
            print(f"✅ 測試結果已保存至: {output_file}")
            print(f"{'='*80}\n")
    except Exception as e:
        # 如果導入失敗或保存失敗，不影響測試執行
        pass
