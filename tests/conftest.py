# 代碼功能說明: pytest 配置和共享 fixtures
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""pytest 配置和共享 fixtures"""

import os
from pathlib import Path

# 在導入其他模塊前加載 .env 文件
try:
    from dotenv import load_dotenv

    # 加載項目根目錄的 .env 文件
    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ 已加載環境變數: {env_path}")
    else:
        print(f"⚠️  .env 文件不存在: {env_path}")
except ImportError:
    print("⚠️  python-dotenv 未安裝，跳過環境變數加載")

import pytest
from typing import Generator, AsyncGenerator
from fastapi.testclient import TestClient
from httpx import AsyncClient
from services.api.core.version import API_PREFIX

# 測試環境配置
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
TEST_API_PREFIX = API_PREFIX


@pytest.fixture(scope="function")
def base_url() -> str:
    """測試基礎 URL"""
    return TEST_BASE_URL


@pytest.fixture(scope="function")
def api_prefix() -> str:
    """API 前綴"""
    return TEST_API_PREFIX


@pytest.fixture(scope="function")
def test_client() -> Generator[TestClient, None, None]:
    """創建 FastAPI 測試客戶端"""
    from services.api.main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """創建異步 HTTP 客戶端"""
    async with AsyncClient(base_url=TEST_BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture(scope="function")
def test_file_content() -> str:
    """測試文件內容"""
    return "這是一個測試文件內容。用於測試文件上傳和處理功能。"


@pytest.fixture(scope="function")
def test_triple_data() -> dict:
    """測試三元組數據"""
    return {
        "subject": {"text": "蘋果公司", "type": "ORG"},
        "relation": {"type": "創立"},
        "object": {"text": "史蒂夫·喬布斯", "type": "PERSON"},
        "confidence": 0.95,
        "context": "測試上下文",
    }


@pytest.fixture(scope="function")
def test_task_simple() -> dict:
    """簡單任務測試數據"""
    return {
        "task": "今天天氣如何？",
        "context": {},
    }


@pytest.fixture(scope="function")
def test_task_complex() -> dict:
    """複雜任務測試數據"""
    return {
        "task": "分析競爭對手並制定應對策略",
        "context": {},
    }
