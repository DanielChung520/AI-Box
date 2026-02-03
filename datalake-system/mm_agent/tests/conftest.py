# 代碼功能說明: MM-Agent 測試配置
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""測試配置文件 - pytest conftest"""

import sys
from pathlib import Path
import pytest

# 添加 datalake-system 目錄到 Python 路徑
datalake_system_dir = Path(__file__).resolve().parent.parent
if str(datalake_system_dir) not in sys.path:
    sys.path.insert(0, str(datalake_system_dir))

# 添加 AI-Box 根目錄到 Python 路徑
ai_box_root = datalake_system_dir.parent
if str(ai_box_root) not in sys.path:
    sys.path.insert(0, str(ai_box_root))


@pytest.fixture(scope="session")
def datalake_system_path():
    """返回 datalake-system 目錄路徑"""
    return datalake_system_dir


@pytest.fixture(scope="session")
def ai_box_root_path():
    """返回 AI-Box 根目錄路徑"""
    return ai_box_root
