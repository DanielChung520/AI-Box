# 代碼功能說明: Ollama 遠端節點簡單連線測試（olm.k84.org）
# 創建日期: 2025-11-26 01:10 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:10 (UTC+8)

"""簡單的連線測試腳本，驗證 olm.k84.org 的連線與對話功能。"""

import os
import pytest
import pytest_asyncio
import httpx

# 從環境變數或預設值取得測試配置
# 注意：olm.k84.org 已透過 tunnel 指向 11434，不需要指定端口
OLLAMA_BASE_URL = os.getenv("TEST_OLLAMA_URL", "http://olm.k84.org")
TEST_MODEL = os.getenv("TEST_OLLAMA_MODEL", "gpt-oss:20b")

# 跳過遠端測試的標記
pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ollama_client():
    """建立 httpx 客戶端用於直接測試 Ollama API。"""
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=60.0) as client:
        yield client


@pytest.mark.skipif(
    os.getenv("SKIP_REMOTE_TESTS", "false").lower() == "true",
    reason="遠端測試已禁用",
)
class TestOllamaRemoteSimple:
    """簡單的遠端 Ollama 節點連線測試。"""

    async def test_health_check(self, ollama_client):
        """測試 Ollama 服務健康檢查。"""
        try:
            response = await ollama_client.get("/api/version", timeout=10.0)
            assert response.status_code == 200
            data = response.json()
            version = data.get("version") or data.get("version_string", "unknown")
            print(f"\n✓ Ollama 版本: {version}")
        except httpx.TimeoutException:
            pytest.fail(f"連線超時: 無法連接到 {OLLAMA_BASE_URL}")
        except httpx.ConnectError as e:
            pytest.fail(f"連線錯誤: 無法連接到 {OLLAMA_BASE_URL} - {e}")

    async def test_list_models(self, ollama_client):
        """測試列出可用模型。"""
        try:
            response = await ollama_client.get("/api/tags", timeout=10.0)
            assert response.status_code == 200
            data = response.json()
            assert "models" in data
            models = [m.get("name") for m in data["models"]]
            print(f"\n✓ 可用模型數量: {len(models)}")
            if models:
                print(f"  前 3 個模型: {', '.join(models[:3])}")
        except httpx.TimeoutException:
            pytest.fail(f"連線超時: 無法連接到 {OLLAMA_BASE_URL}")
        except httpx.ConnectError as e:
            pytest.fail(f"連線錯誤: 無法連接到 {OLLAMA_BASE_URL} - {e}")

    async def test_chat_completion(self, ollama_client):
        """測試對話完成功能。"""
        payload = {
            "model": TEST_MODEL,
            "messages": [
                {"role": "system", "content": "你是一個友善的助手。請用簡短的回答。"},
                {"role": "user", "content": "請回答：你好"},
            ],
            "stream": False,
        }
        try:
            response = await ollama_client.post(
                "/api/chat",
                json=payload,
                timeout=120.0,  # 對話可能需要更長時間
            )
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            message_content = data["message"].get("content", "")
            assert len(message_content) > 0
            print(f"\n✓ Chat 回應: {message_content[:150]}...")
        except httpx.TimeoutException:
            pytest.fail(f"請求超時: 模型 {TEST_MODEL} 回應時間過長")
        except httpx.ConnectError as e:
            pytest.fail(f"連線錯誤: 無法連接到 {OLLAMA_BASE_URL} - {e}")

    async def test_generate(self, ollama_client):
        """測試文本生成功能。"""
        payload = {
            "model": TEST_MODEL,
            "prompt": "簡短回答（10 個字以內）：Python 是什麼？",
            "stream": False,
        }
        try:
            response = await ollama_client.post(
                "/api/generate",
                json=payload,
                timeout=120.0,
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            response_text = data["response"]
            assert len(response_text) > 0
            print(f"\n✓ Generate 回應: {response_text[:150]}...")
        except httpx.TimeoutException:
            pytest.fail(f"請求超時: 模型 {TEST_MODEL} 回應時間過長")
        except httpx.ConnectError as e:
            pytest.fail(f"連線錯誤: 無法連接到 {OLLAMA_BASE_URL} - {e}")


if __name__ == "__main__":
    # 允許直接執行此檔案進行測試
    pytest.main([__file__, "-v", "-s"])
