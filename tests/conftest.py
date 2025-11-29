# 代碼功能說明: pytest 配置和共享 fixtures
# 創建日期: 2025-11-29
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-29

"""pytest 配置和共享測試 fixtures。"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.task_analyzer.models import TaskClassificationResult, TaskType


@pytest.fixture
def mock_openai_client():
    """模擬 OpenAI 客戶端。"""
    mock_client = AsyncMock()
    mock_client.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[MagicMock(text="Test response")],
            usage=MagicMock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
        )
    )
    mock_client.chat.completions.create = AsyncMock(
        return_value=MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(content="Test chat response"),
                )
            ],
            usage=MagicMock(
                prompt_tokens=10,
                completion_tokens=20,
                total_tokens=30,
            ),
        )
    )
    mock_client.embeddings.create = AsyncMock(
        return_value=MagicMock(
            data=[MagicMock(embedding=[0.1, 0.2, 0.3])],
        )
    )
    return mock_client


@pytest.fixture
def sample_task_classification():
    """示例任務分類結果。"""
    return TaskClassificationResult(
        task_type=TaskType.QUERY,
        confidence=0.9,
        reasoning="Test task classification",
    )


@pytest.fixture
def sample_messages():
    """示例消息列表。"""
    return [
        {"role": "user", "content": "Hello, how are you?"},
        {"role": "assistant", "content": "I'm doing well, thank you!"},
    ]


@pytest.fixture(autouse=True)
def setup_env_vars(monkeypatch):
    """設置測試環境變數。"""
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")
    monkeypatch.setenv("GROK_API_KEY", "test-grok-key")
    monkeypatch.setenv("QWEN_API_KEY", "test-qwen-key")
