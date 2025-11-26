# 代碼功能說明: Ollama 遠端節點整合測試（olm.k84.org）
# 創建日期: 2025-11-26 01:05 (UTC+8)
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-26 01:05 (UTC+8)

"""測試透過 olm.k84.org 連線並執行對話/生成/embeddings 功能。"""

import os
import pytest
import httpx

# 從環境變數或預設值取得測試配置
OLLAMA_HOST = os.getenv("TEST_OLLAMA_HOST", "olm.k84.org")
OLLAMA_PORT = int(os.getenv("TEST_OLLAMA_PORT", "11434"))
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
TEST_MODEL = os.getenv("TEST_OLLAMA_MODEL", "gpt-oss:20b")
TEST_EMBEDDING_MODEL = os.getenv("TEST_OLLAMA_EMBEDDING_MODEL", "gpt-oss:20b")

# 跳過遠端測試的標記（如果需要）
pytestmark = pytest.mark.asyncio


@pytest.fixture
async def ollama_client():
    """建立 httpx 客戶端用於直接測試 Ollama API。"""
    async with httpx.AsyncClient(base_url=OLLAMA_BASE_URL, timeout=30.0) as client:
        yield client


@pytest.mark.skipif(
    os.getenv("SKIP_REMOTE_TESTS", "false").lower() == "true",
    reason="遠端測試已禁用",
)
class TestOllamaRemoteConnection:
    """測試遠端 Ollama 節點的連線與基本功能。"""

    async def test_health_check(self, ollama_client):
        """測試 Ollama 服務健康檢查。"""
        response = await ollama_client.get("/api/version")
        assert response.status_code == 200
        data = response.json()
        assert "version" in data or "version_string" in data
        print(f"✓ Ollama 版本: {data.get('version') or data.get('version_string')}")

    async def test_list_models(self, ollama_client):
        """測試列出可用模型。"""
        response = await ollama_client.get("/api/tags")
        assert response.status_code == 200
        data = response.json()
        assert "models" in data
        models = [m.get("name") for m in data["models"]]
        print(f"✓ 可用模型: {', '.join(models[:5])}...")  # 只顯示前5個

    async def test_chat_completion(self, ollama_client):
        """測試對話完成功能。"""
        payload = {
            "model": TEST_MODEL,
            "messages": [
                {"role": "system", "content": "你是一個友善的助手。"},
                {"role": "user", "content": "請簡單回答：你好"},
            ],
            "stream": False,
        }
        response = await ollama_client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        message_content = data["message"].get("content", "")
        assert len(message_content) > 0
        print(f"✓ Chat 回應: {message_content[:100]}...")

    async def test_generate(self, ollama_client):
        """測試文本生成功能。"""
        payload = {
            "model": TEST_MODEL,
            "prompt": "簡短回答：Python 是什麼？",
            "stream": False,
        }
        response = await ollama_client.post("/api/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        response_text = data["response"]
        assert len(response_text) > 0
        print(f"✓ Generate 回應: {response_text[:100]}...")

    async def test_embeddings(self, ollama_client):
        """測試向量嵌入功能。"""
        payload = {
            "model": TEST_EMBEDDING_MODEL,
            "prompt": "測試文本",
        }
        response = await ollama_client.post("/api/embeddings", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        embedding = data["embedding"]
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        print(f"✓ Embedding 維度: {len(embedding)}")


@pytest.mark.skipif(
    os.getenv("SKIP_REMOTE_TESTS", "false").lower() == "true",
    reason="遠端測試已禁用",
)
class TestOllamaClientIntegration:
    """測試使用 OllamaClient 類別進行整合測試。"""

    @pytest.fixture
    def mock_settings(self, monkeypatch):
        """模擬 Ollama 設定以使用遠端節點。"""
        from llm.router import LLMNodeConfig
        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.nodes = [
            LLMNodeConfig(
                name="olm-k84-org",
                host=OLLAMA_HOST,
                port=OLLAMA_PORT,
                weight=1,
            )
        ]
        mock_settings.router_strategy = "round_robin"
        mock_settings.router_cooldown = 30
        mock_settings.timeout = 30.0
        mock_settings.api_token = None
        mock_settings.default_model = TEST_MODEL
        mock_settings.embedding_model = TEST_EMBEDDING_MODEL

        return mock_settings

    async def test_client_chat(self, mock_settings, monkeypatch):
        """測試使用 OllamaClient 進行對話。"""
        from services.api.clients.ollama_client import OllamaClient

        # 暫時覆寫設定
        monkeypatch.setattr(
            "services.api.clients.ollama_client.get_ollama_settings",
            lambda: mock_settings,
        )

        client = OllamaClient()
        result = await client.chat(
            model=TEST_MODEL,
            messages=[
                {"role": "user", "content": "用一句話回答：什麼是 AI？"},
            ],
            stream=False,
        )
        assert "message" in result or "response" in result
        print("✓ OllamaClient Chat 成功")

    async def test_client_generate(self, mock_settings, monkeypatch):
        """測試使用 OllamaClient 進行生成。"""
        from services.api.clients.ollama_client import OllamaClient

        monkeypatch.setattr(
            "services.api.clients.ollama_client.get_ollama_settings",
            lambda: mock_settings,
        )

        client = OllamaClient()
        result = await client.generate(
            model=TEST_MODEL,
            prompt="簡短回答：什麼是機器學習？",
            stream=False,
        )
        assert "response" in result
        response_text = result["response"]
        assert len(response_text) > 0
        print(f"✓ OllamaClient Generate 成功: {response_text[:50]}...")

    async def test_client_embeddings(self, mock_settings, monkeypatch):
        """測試使用 OllamaClient 進行向量嵌入。"""
        from services.api.clients.ollama_client import OllamaClient

        monkeypatch.setattr(
            "services.api.clients.ollama_client.get_ollama_settings",
            lambda: mock_settings,
        )

        client = OllamaClient()
        result = await client.embeddings(
            model=TEST_EMBEDDING_MODEL,
            prompt="測試嵌入文本",
        )
        assert "embedding" in result
        embedding = result["embedding"]
        assert isinstance(embedding, list) and len(embedding) > 0
        print(f"✓ OllamaClient Embeddings 成功: 維度 {len(embedding)}")


if __name__ == "__main__":
    # 允許直接執行此檔案進行測試
    pytest.main([__file__, "-v", "-s"])
