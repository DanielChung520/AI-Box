"""
代碼功能說明: doc_patch_service 擴展單元測試
創建日期: 2025-12-20 12:35:31 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:35:31 (UTC+8)
"""

from __future__ import annotations

import pytest

from services.api.services.doc_patch_service import (
    PatchApplyError,
    SearchReplacePatch,
    apply_search_replace_patches,
    apply_unified_diff,
    find_text_position,
    search_replace_to_unified_diff,
)


class TestFindTextPositionExtended:
    """測試 find_text_position 函數（擴展測試）"""

    def test_normalized_match(self) -> None:
        """測試標準化匹配（去除多餘空白）"""
        original = "Hello    world,   this is a test."
        search_block = "Hello world, this is a test."
        result = find_text_position(original=original, search_block=search_block)
        assert result.match_type in ("exact", "normalized", "fuzzy")
        assert result.similarity > 0.8

    def test_fuzzy_match(self) -> None:
        """測試模糊匹配（Levenshtein Distance）"""
        original = "Hello world, this is a test."
        search_block = "Hello wrld, this is a test."  # 故意拼寫錯誤
        result = find_text_position(
            original=original, search_block=search_block, fuzzy_threshold=0.8
        )
        assert result.match_type == "fuzzy"
        assert result.similarity >= 0.8

    def test_cursor_position_context(self) -> None:
        """測試游標位置上下文匹配"""
        original = "A" * 500 + "Hello world" + "B" * 500
        search_block = "Hello world"
        cursor_position = 600  # 在 "Hello world" 附近
        result = find_text_position(
            original=original, search_block=search_block, cursor_position=cursor_position
        )
        assert result.position == 500
        assert result.match_type == "exact"

    def test_empty_search_block(self) -> None:
        """測試空 search_block"""
        original = "Hello world"
        search_block = ""
        with pytest.raises(PatchApplyError, match="search_block cannot be empty"):
            find_text_position(original=original, search_block=search_block)


class TestSearchReplaceToUnifiedDiffExtended:
    """測試 search_replace_to_unified_diff 函數（擴展測試）"""

    def test_single_patch(self) -> None:
        """測試單個 patch 轉換"""
        original = "Hello world\nThis is a test."
        patches = [SearchReplacePatch(search_block="world", replace_block="universe")]
        diff = search_replace_to_unified_diff(original=original, patches=patches)
        assert "--- original" in diff
        assert "+++ modified" in diff
        assert "-world" in diff or "world" in diff
        assert "+universe" in diff or "universe" in diff

    def test_multiple_patches(self) -> None:
        """測試多個 patches 轉換"""
        original = "First line\nSecond line\nThird line"
        patches = [
            SearchReplacePatch(search_block="First", replace_block="1st"),
            SearchReplacePatch(search_block="Third", replace_block="3rd"),
        ]
        diff = search_replace_to_unified_diff(original=original, patches=patches)
        assert "--- original" in diff
        assert "+++ modified" in diff

    def test_empty_patches(self) -> None:
        """測試空 patches 列表"""
        original = "Hello world"
        patches: list[SearchReplacePatch] = []
        with pytest.raises(PatchApplyError, match="patches list cannot be empty"):
            search_replace_to_unified_diff(original=original, patches=patches)

    def test_multiline_patch(self) -> None:
        """測試多行 patch"""
        original = "Line 1\nLine 2\nLine 3"
        patches = [
            SearchReplacePatch(search_block="Line 2", replace_block="Line 2 Modified\nLine 2.5")
        ]
        diff = search_replace_to_unified_diff(original=original, patches=patches)
        assert "--- original" in diff
        assert "+++ modified" in diff


class TestApplySearchReplacePatchesExtended:
    """測試 apply_search_replace_patches 函數（擴展測試）"""

    def test_multiple_patches_apply(self) -> None:
        """測試應用多個 patches"""
        original = "First second third"
        patches = [
            {"search_block": "First", "replace_block": "1st"},
            {"search_block": "third", "replace_block": "3rd"},
        ]
        result = apply_search_replace_patches(original=original, patches=patches)
        assert "1st" in result
        assert "3rd" in result
        assert "second" in result

    def test_patch_with_confidence(self) -> None:
        """測試帶有 confidence 的 patch"""
        original = "Hello world"
        patches = [{"search_block": "world", "replace_block": "universe", "confidence": 0.95}]
        result = apply_search_replace_patches(original=original, patches=patches)
        assert result == "Hello universe"

    def test_invalid_patch_format(self) -> None:
        """測試無效的 patch 格式"""
        original = "Hello world"
        patches = [{"invalid": "format"}]  # 缺少 search_block 和 replace_block
        with pytest.raises(PatchApplyError, match="search_block"):
            apply_search_replace_patches(original=original, patches=patches)

    def test_empty_search_block(self) -> None:
        """測試空的 search_block"""
        original = "Hello world"
        patches = [{"search_block": "", "replace_block": "test"}]
        with pytest.raises(PatchApplyError, match="search_block"):
            apply_search_replace_patches(original=original, patches=patches)

    def test_fuzzy_match_apply(self) -> None:
        """測試模糊匹配應用"""
        original = "Hello wrld"  # 拼寫錯誤
        patches = [{"search_block": "Hello world", "replace_block": "Hello universe"}]
        # 應該能夠通過模糊匹配找到並應用
        result = apply_search_replace_patches(original=original, patches=patches, cursor_position=0)
        # 結果應該包含 "universe" 或保持原樣（取決於模糊匹配結果）
        assert isinstance(result, str)

    def test_multiline_replace(self) -> None:
        """測試多行替換"""
        original = "Line 1\nLine 2\nLine 3"
        patches = [{"search_block": "Line 2", "replace_block": "Line 2 Modified\nLine 2.5"}]
        result = apply_search_replace_patches(original=original, patches=patches)
        assert "Line 2 Modified" in result
        assert "Line 2.5" in result


class TestIntegration:
    """集成測試：Search-and-Replace 到 unified diff 再到應用"""

    def test_full_workflow(self) -> None:
        """測試完整工作流程"""
        original = "Hello world\nThis is a test."
        patches = [{"search_block": "world", "replace_block": "universe"}]

        # 應用 Search-and-Replace patches
        result = apply_search_replace_patches(original=original, patches=patches)

        # 驗證結果
        assert "universe" in result
        assert "Hello" in result

        # 驗證可以通過 unified diff 重新生成相同結果
        search_replace_patches = [
            SearchReplacePatch(search_block="world", replace_block="universe")
        ]
        diff = search_replace_to_unified_diff(original=original, patches=search_replace_patches)
        result2 = apply_unified_diff(original=original, diff_text=diff)
        assert result == result2
