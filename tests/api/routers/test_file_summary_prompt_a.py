# 代碼功能說明: Prompt A 語意摘要員單元測試
# 創建日期: 2026-01-21
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-21

"""Prompt A 語意摘要員單元測試 - 測試文件摘要生成功能

測試場景：
1. 正常情況下生成結構化摘要
2. 長文本截斷處理
3. JSON 解析錯誤處理
4. LLM 調用失敗處理
"""

from unittest.mock import AsyncMock, patch

import pytest


class MockMoEResult:
    """模擬 MoE 生成結果"""

    def __init__(self, text: str):
        self.text = text
        self.content = text

    def get(self, key: str, default: str = "") -> str:
        """支援 dict.get() 風格的訪問"""
        if key in ("text", "content"):
            return getattr(self, key, default)
        return default


@pytest.fixture
def mock_moe_manager():
    """創建模擬的 MoE 管理器"""
    moe = AsyncMock()
    return moe


@pytest.fixture
def sample_full_text():
    """範例：完整的文件文本"""
    return """# 國琿機械熱解爐操作手冊

## 1. 產品介紹
國琿機械熱解爐是一款專業的廢棄物處理設備，採用高溫熱解技術將廢棄物轉化為能源。

## 2. 安全注意事項
操作人員必須穿戴防護裝備，包括耐高溫手套、護目鏡和防護服。

## 3. 操作流程
3.1 啟動前檢查
3.2 啟動設備
3.3 監控運行參數
3.4 正常關機程序

## 4. 維護保養
4.1 日常檢查項目
4.2 每週維護任務
4.3 每月定期保養
4.4 故障排除指南

本手冊適用於技術人員操作和維護熱解爐設備。
"""


@pytest.fixture
def sample_long_text():
    """範例：長文本（超過截斷長度）"""
    base_text = "這是一個技術文檔，討論機器學習模型訓練和部署。\n" * 1000
    return base_text


class TestGenerateFileSummaryForMetadata:
    """測試 _generate_file_summary_for_metadata 函數"""

    @pytest.mark.asyncio
    async def test_generate_summary_success(self, mock_moe_manager, sample_full_text):
        """測試正常情況下生成結構化摘要"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        mock_response = """{
            "theme": "國琿機械熱解爐操作手冊",
            "structure_outline": [
                {"chapter": "產品介紹", "core_logic": "介紹熱解爐設備和技術原理"},
                {"chapter": "安全注意事項", "core_logic": "說明操作安全規範"},
                {"chapter": "操作流程", "core_logic": "詳細步驟指引"},
                {"chapter": "維護保養", "core_logic": "設備維護指南"}
            ],
            "key_terms": ["熱解爐", "高溫熱解", "廢棄物處理", "能源轉化", "操作人員"],
            "target_audience": "技術員"
        }"""

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-file-123",
                file_name="熱解爐操作手冊.pdf",
                full_text=sample_full_text,
                user_id="user-456",
            )

        assert result is not None
        assert "theme" in result
        assert "structure_outline" in result
        assert "key_terms" in result
        assert "target_audience" in result
        assert result["theme"] == "國琿機械熱解爐操作手冊"
        assert len(result["key_terms"]) == 5
        assert result["target_audience"] == "技術員"

    @pytest.mark.asyncio
    async def test_generate_summary_with_text_truncation(self, mock_moe_manager, sample_long_text):
        """測試長文本截斷處理"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        mock_response = """{
            "theme": "機器學習技術文檔",
            "structure_outline": [
                {"chapter": "模型訓練", "core_logic": "訓練流程說明"}
            ],
            "key_terms": ["機器學習", "模型訓練"],
            "target_audience": "技術員"
        }"""

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-file-long",
                file_name="機器學習文檔.pdf",
                full_text=sample_long_text,
                user_id="user-789",
            )

        assert result is not None
        assert result["theme"] == "機器學習技術文檔"
        mock_moe_manager.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_summary_json_decode_error(self, mock_moe_manager, sample_full_text):
        """測試 JSON 解析錯誤時返回 None"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        invalid_json_response = "這不是有效的 JSON 格式"

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(invalid_json_response))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-file-invalid",
                file_name="測試文檔.pdf",
                full_text=sample_full_text,
                user_id="user-abc",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_summary_llm_exception(self, sample_full_text):
        """測試 LLM 調用異常處理"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        mock_moe_manager = AsyncMock()
        mock_moe_manager.generate = AsyncMock(side_effect=Exception("LLM 服務不可用"))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-file-error",
                file_name="錯誤測試.pdf",
                full_text=sample_full_text,
                user_id="user-error",
            )

        assert result is None

    @pytest.mark.asyncio
    async def test_generate_summary_with_extracted_json(self, mock_moe_manager, sample_full_text):
        """測試從響應文本中提取 JSON"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        response_with_text = """以下是分析結果：

```json
{
    "theme": "設備操作手冊",
    "structure_outline": [
        {"chapter": "簡介", "core_logic": "設備概述"}
    ],
    "key_terms": ["設備", "操作"],
    "target_audience": "一般用戶"
}
```

希望這個摘要對您有幫助。
"""

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(response_with_text))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-file-extract",
                file_name="設備手冊.pdf",
                full_text=sample_full_text,
                user_id="user-extract",
            )

        assert result is not None
        assert result["theme"] == "設備操作手冊"
        assert result["target_audience"] == "一般用戶"


class TestPromptASpecificationCompliance:
    """測試 Prompt A 規格遵循"""

    @pytest.mark.asyncio
    async def test_prompt_contains_all_required_fields(self, mock_moe_manager, sample_full_text):
        """測試 Prompt 包含所有必要字段"""

        from api.routers.file_upload import _generate_file_summary_for_metadata

        captured_prompt = None

        async def capture_prompt(*args, **kwargs):
            nonlocal captured_prompt
            captured_prompt = args[0] if args else kwargs.get("prompt", "")
            return MockMoEResult(
                '{"theme": "測試", "structure_outline": [], "key_terms": [], "target_audience": "技術員"}'
            )

        mock_moe_manager.generate = AsyncMock(side_effect=capture_prompt)

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            await _generate_file_summary_for_metadata(
                file_id="test-prompt",
                file_name="測試.pdf",
                full_text=sample_full_text,
                user_id="user-prompt",
            )

        assert captured_prompt is not None
        assert "主題定義" in captured_prompt
        assert "結構大綱" in captured_prompt
        assert "關鍵術語" in captured_prompt
        assert "目標受眾" in captured_prompt
        assert "JSON 格式" in captured_prompt

    @pytest.mark.asyncio
    async def test_returns_valid_structure(self, mock_moe_manager, sample_full_text):
        """測試返回結構符合規格"""
        from api.routers.file_upload import _generate_file_summary_for_metadata

        mock_response = """{
            "theme": "測試文檔",
            "structure_outline": [
                {"chapter": "第一章", "core_logic": "核心邏輯一"},
                {"chapter": "第二章", "core_logic": "核心邏輯二"}
            ],
            "key_terms": ["術語A", "術語B", "術語C"],
            "target_audience": "投資人"
        }"""

        mock_moe_manager.generate = AsyncMock(return_value=MockMoEResult(mock_response))

        with patch("llm.moe.moe_manager.LLMMoEManager", return_value=mock_moe_manager):
            result = await _generate_file_summary_for_metadata(
                file_id="test-structure",
                file_name="結構測試.pdf",
                full_text=sample_full_text,
                user_id="user-structure",
            )

        assert isinstance(result, dict)
        assert isinstance(result.get("structure_outline"), list)
        for item in result.get("structure_outline", []):
            assert "chapter" in item
            assert "core_logic" in item
        assert isinstance(result.get("key_terms"), list)
        assert result["target_audience"] in ["技術員", "投資人", "一般用戶"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
