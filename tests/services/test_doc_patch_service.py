"""
代碼功能說明: doc_patch_service 單元測試
創建日期: 2025-12-20 12:30:07 (UTC+8)
創建人: Daniel Chung
最後修改日期: 2025-12-20 12:30:07 (UTC+8)
"""

from __future__ import annotations

import pytest

from services.api.services.doc_patch_service import (
    PatchApplyError,
    apply_search_replace_patches,
    find_text_position,
)


class TestFindTextPosition:
    """測試 find_text_position 函數"""

    def test_exact_match(self) -> None:
        """測試精確匹配"""
        original = "Hello world, this is a test."
        search_block = "world"
        result = find_text_position(original=original, search_block=search_block)
        assert result.position == 6
        assert result.match_type == "exact"
        assert result.similarity == 1.0

    def test_exact_match_not_found(self) -> None:
        """測試精確匹配失敗"""
        original = "Hello world"
        search_block = "not found"
        with pytest.raises(PatchApplyError, match="Could not find search_block"):
            find_text_position(original=original, search_block=search_block)


class TestApplySearchReplacePatches:
    """測試 apply_search_replace_patches 函數"""

    def test_single_patch_apply(self) -> None:
        """測試應用單個 patch"""
        original = "Hello world"
        patches = [{"search_block": "world", "replace_block": "universe"}]
        result = apply_search_replace_patches(original=original, patches=patches)
        assert result == "Hello universe"
