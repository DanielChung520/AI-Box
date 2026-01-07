# 代碼功能說明: DocumentEditingService 單元測試
# 創建日期: 2026-01-06
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-06

"""DocumentEditingService 單元測試

測試文檔編輯服務的核心功能，包括：
- generate_editing_patches() 方法
- convert_to_search_replace_patches() 方法
- _build_patch_prompt() 方法
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.core.execution.document_editing_service import DocumentEditingService


@pytest.fixture
def editing_service():
    """創建 DocumentEditingService 實例"""
    return DocumentEditingService()


@pytest.fixture
def sample_file_content():
    """示例文件內容"""
    return "# 標題\n\n這是原始內容。\n\n## 子標題\n\n更多內容。"


@pytest.fixture
def sample_search_replace_response():
    """示例 Search-and-Replace 格式響應"""
    return {
        "patches": [
            {
                "search_block": "這是原始內容。",
                "replace_block": "這是修改後的內容。",
            }
        ],
        "thought_chain": "優化了文字表達",
    }


@pytest.fixture
def sample_json_patch_response():
    """示例 JSON Patch 格式響應"""
    return [
        {"op": "replace", "path": "/content", "value": "新內容"},
    ]


@pytest.mark.asyncio
class TestDocumentEditingService:
    """DocumentEditingService 測試類"""

    async def test_generate_editing_patches_search_replace(
        self,
        editing_service,
        sample_file_content,
        sample_search_replace_response,
    ):
        """測試生成 Search-and-Replace 格式的 patches"""
        instruction = "優化文字表達"

        with patch.object(
            editing_service, "_call_llm_for_patch", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = (
                "search_replace",
                sample_search_replace_response,
                "優化了文字表達",
            )

            patch_kind, patch_payload, summary = await editing_service.generate_editing_patches(
                instruction=instruction,
                file_content=sample_file_content,
                doc_format="md",
            )

            assert patch_kind == "search_replace"
            assert isinstance(patch_payload, dict)
            assert "patches" in patch_payload
            assert summary == "優化了文字表達"
            mock_llm.assert_called_once()

    async def test_generate_editing_patches_unified_diff(
        self,
        editing_service,
        sample_file_content,
    ):
        """測試生成 unified_diff 格式的 patches"""
        instruction = "修改內容"

        with patch.object(
            editing_service, "_call_llm_for_patch", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = (
                "unified_diff",
                "--- a/file.md\n+++ b/file.md\n@@ -1,1 +1,1 @@\n-原始\n+修改",
                "",
            )

            patch_kind, patch_payload, summary = await editing_service.generate_editing_patches(
                instruction=instruction,
                file_content=sample_file_content,
                doc_format="md",
            )

            assert patch_kind == "unified_diff"
            assert isinstance(patch_payload, str)
            assert summary == ""

    async def test_generate_editing_patches_json_patch(
        self,
        editing_service,
        sample_file_content,
        sample_json_patch_response,
    ):
        """測試生成 JSON Patch 格式的 patches"""
        instruction = "修改 JSON 內容"

        with patch.object(
            editing_service, "_call_llm_for_patch", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = (
                "json_patch",
                sample_json_patch_response,
                "",
            )

            patch_kind, patch_payload, summary = await editing_service.generate_editing_patches(
                instruction=instruction,
                file_content='{"content": "原始"}',
                doc_format="json",
            )

            assert patch_kind == "json_patch"
            assert isinstance(patch_payload, list)
            assert summary == ""

    async def test_generate_editing_patches_with_cursor_position(
        self,
        editing_service,
        sample_file_content,
    ):
        """測試帶游標位置的 patches 生成"""
        instruction = "在游標位置插入內容"
        cursor_position = 10

        with patch.object(
            editing_service, "_call_llm_for_patch", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.return_value = (
                "search_replace",
                {"patches": []},
                "",
            )

            await editing_service.generate_editing_patches(
                instruction=instruction,
                file_content=sample_file_content,
                doc_format="md",
                cursor_position=cursor_position,
            )

            # 驗證 prompt 構建時使用了游標位置
            call_args = mock_llm.call_args
            assert call_args is not None

    async def test_generate_editing_patches_llm_error(
        self,
        editing_service,
        sample_file_content,
    ):
        """測試 LLM 調用失敗的錯誤處理"""
        instruction = "測試指令"

        with patch.object(
            editing_service, "_call_llm_for_patch", new_callable=AsyncMock
        ) as mock_llm:
            mock_llm.side_effect = Exception("LLM 調用失敗")

            with pytest.raises(Exception) as exc_info:
                await editing_service.generate_editing_patches(
                    instruction=instruction,
                    file_content=sample_file_content,
                    doc_format="md",
                )

            assert "LLM 調用失敗" in str(exc_info.value)

    def test_convert_to_search_replace_patches_valid(
        self,
        editing_service,
        sample_search_replace_response,
    ):
        """測試轉換 Search-and-Replace 格式 - 有效格式"""
        patches = editing_service.convert_to_search_replace_patches(
            "search_replace", sample_search_replace_response
        )

        assert isinstance(patches, list)
        assert len(patches) == 1
        assert patches[0]["search_block"] == "這是原始內容。"
        assert patches[0]["replace_block"] == "這是修改後的內容。"

    def test_convert_to_search_replace_patches_invalid_dict(
        self,
        editing_service,
    ):
        """測試轉換 Search-and-Replace 格式 - 無效字典"""
        patches = editing_service.convert_to_search_replace_patches(
            "search_replace", {"invalid": "data"}
        )

        assert isinstance(patches, list)
        assert len(patches) == 0

    def test_convert_to_search_replace_patches_unsupported_format(
        self,
        editing_service,
    ):
        """測試轉換不支持的格式"""
        patches = editing_service.convert_to_search_replace_patches(
            "unified_diff", "--- a/file.md\n+++ b/file.md"
        )

        assert isinstance(patches, list)
        assert len(patches) == 0

    def test_build_patch_prompt_markdown(
        self,
        editing_service,
        sample_file_content,
    ):
        """測試構建 Markdown 格式的 Prompt"""
        prompt = editing_service._build_patch_prompt(
            doc_format="md",
            instruction="測試指令",
            base_content=sample_file_content,
        )

        assert isinstance(prompt, str)
        assert "測試指令" in prompt
        assert sample_file_content in prompt
        assert "search_block" in prompt
        assert "replace_block" in prompt

    def test_build_patch_prompt_json(
        self,
        editing_service,
    ):
        """測試構建 JSON 格式的 Prompt"""
        json_content = '{"key": "value"}'
        prompt = editing_service._build_patch_prompt(
            doc_format="json",
            instruction="修改 JSON",
            base_content=json_content,
        )

        assert isinstance(prompt, str)
        assert "修改 JSON" in prompt
        assert json_content in prompt
        assert "JSON Patch" in prompt
        assert "RFC6902" in prompt

    def test_build_patch_prompt_with_cursor_position(
        self,
        editing_service,
        sample_file_content,
    ):
        """測試構建帶游標位置的 Prompt"""
        cursor_position = 10
        prompt = editing_service._build_patch_prompt(
            doc_format="md",
            instruction="測試指令",
            base_content=sample_file_content,
            cursor_position=cursor_position,
        )

        assert isinstance(prompt, str)
        assert "游標位置" in prompt
        assert str(cursor_position) in prompt

    def test_build_patch_prompt_cursor_context_window(
        self,
        editing_service,
    ):
        """測試游標上下文窗口"""
        # 創建一個長文件內容
        long_content = "A" * 5000 + "B" * 5000
        cursor_position = 5000

        prompt = editing_service._build_patch_prompt(
            doc_format="md",
            instruction="測試",
            base_content=long_content,
            cursor_position=cursor_position,
        )

        # 驗證上下文窗口（前後各 1000 字符）
        assert "游標位置" in prompt
        # 上下文應該包含游標附近的內容
        context_start = max(0, cursor_position - 1000)
        context_end = min(len(long_content), cursor_position + 1000)
        expected_context = long_content[context_start:context_end]
        assert expected_context in prompt

    async def test_call_llm_for_patch_search_replace_format(
        self,
        editing_service,
        sample_search_replace_response,
    ):
        """測試 LLM 調用 - Search-and-Replace 格式"""
        prompt = "測試 prompt"

        with patch(
            "agents.core.execution.document_editing_service.LLMMoEManager"
        ) as mock_moe_class:
            mock_moe = MagicMock()
            mock_moe.generate = AsyncMock(
                return_value={"content": str(sample_search_replace_response).replace("'", '"')}
            )
            mock_moe_class.return_value = mock_moe

            # 需要正確的 JSON 字符串
            import json

            json_response = json.dumps(sample_search_replace_response)
            mock_moe.generate.return_value = {"content": json_response}

            patch_kind, patch_payload, summary = await editing_service._call_llm_for_patch(prompt)

            assert patch_kind == "search_replace"
            assert isinstance(patch_payload, dict)
            assert "patches" in patch_payload
            assert summary == "優化了文字表達"

    async def test_call_llm_for_patch_json_patch_format(
        self,
        editing_service,
        sample_json_patch_response,
    ):
        """測試 LLM 調用 - JSON Patch 格式"""
        prompt = "測試 prompt"

        with patch(
            "agents.core.execution.document_editing_service.LLMMoEManager"
        ) as mock_moe_class:
            mock_moe = MagicMock()
            import json

            json_response = json.dumps(sample_json_patch_response)
            mock_moe.generate = AsyncMock(return_value={"content": json_response})
            mock_moe_class.return_value = mock_moe

            patch_kind, patch_payload, summary = await editing_service._call_llm_for_patch(prompt)

            assert patch_kind == "json_patch"
            assert isinstance(patch_payload, list)
            assert summary == ""

    async def test_call_llm_for_patch_invalid_json(
        self,
        editing_service,
    ):
        """測試 LLM 調用 - 無效 JSON"""
        prompt = "測試 prompt"

        with patch(
            "agents.core.execution.document_editing_service.LLMMoEManager"
        ) as mock_moe_class:
            mock_moe = MagicMock()
            mock_moe.generate = AsyncMock(return_value={"content": "無效的 JSON 內容"})
            mock_moe_class.return_value = mock_moe

            patch_kind, patch_payload, summary = await editing_service._call_llm_for_patch(prompt)

            # 應該回退到 unified_diff 格式
            assert patch_kind == "unified_diff"
            assert isinstance(patch_payload, str)
            assert summary == ""

    async def test_call_llm_for_patch_empty_response(
        self,
        editing_service,
    ):
        """測試 LLM 調用 - 空響應"""
        prompt = "測試 prompt"

        with patch(
            "agents.core.execution.document_editing_service.LLMMoEManager"
        ) as mock_moe_class:
            mock_moe = MagicMock()
            mock_moe.generate = AsyncMock(return_value={"content": ""})
            mock_moe_class.return_value = mock_moe

            patch_kind, patch_payload, summary = await editing_service._call_llm_for_patch(prompt)

            # 應該回退到 unified_diff 格式
            assert patch_kind == "unified_diff"
            assert isinstance(patch_payload, str)
            assert summary == ""
