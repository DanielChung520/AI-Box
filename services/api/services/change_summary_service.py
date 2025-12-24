# 代碼功能說明: 變更摘要生成服務
# 創建日期: 2025-12-20
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-20

"""變更摘要生成服務 - 使用 LLM 生成文檔變更的摘要"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 單例實例
_change_summary_service: Optional["ChangeSummaryService"] = None


def get_change_summary_service() -> "ChangeSummaryService":
    """獲取變更摘要服務實例（單例模式）"""
    global _change_summary_service
    if _change_summary_service is None:
        _change_summary_service = ChangeSummaryService()
    return _change_summary_service


class ChangeSummaryService:
    """變更摘要生成服務"""

    def __init__(self) -> None:
        """初始化服務"""
        pass

    async def generate_summary(
        self,
        original_content: str,
        modified_content: str,
        patches: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        生成變更摘要

        Args:
            original_content: 原始文件內容
            modified_content: 修改後的文件內容
            patches: 可選的變更 patches 列表（如果可用）

        Returns:
            變更摘要文本（200 字以內）
        """
        try:
            from llm.moe.moe_manager import LLMMoEManager

            # 構建提示詞
            prompt = self._build_summary_prompt(original_content, modified_content, patches)

            # 調用 LLM 生成摘要
            moe = LLMMoEManager()
            result = await moe.generate(
                prompt,
                temperature=0.7,
                max_tokens=300,  # 限制 token 數以確保摘要簡潔
            )

            # 提取生成的摘要
            summary = str(result.get("content") or result.get("text") or "")
            summary = summary.strip()

            # 如果摘要過長，截斷到 200 字以內
            if len(summary) > 200:
                summary = summary[:197] + "..."

            # 如果摘要為空，生成默認摘要
            if not summary:
                summary = self._generate_default_summary(original_content, modified_content)

            logger.info(f"變更摘要生成成功，長度: {len(summary)}")
            return summary

        except Exception as e:
            logger.error(f"生成變更摘要失敗: {e}", exc_info=True)
            # 失敗時返回默認摘要
            return self._generate_default_summary(original_content, modified_content)

    def _build_summary_prompt(
        self,
        original_content: str,
        modified_content: str,
        patches: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        構建摘要生成的提示詞

        Args:
            original_content: 原始文件內容
            modified_content: 修改後的文件內容
            patches: 可選的變更 patches 列表

        Returns:
            提示詞文本
        """
        # 如果提供了 patches，使用 patches 信息
        if patches and len(patches) > 0:
            patches_text = "\n".join(
                [
                    f"- {i+1}. {patch.get('modifiedText', '')[:100]}"
                    for i, patch in enumerate(patches[:10])  # 最多顯示 10 個變更
                ]
            )
            prompt = f"""請將以下文檔修改片段總結為一份 200 字以內的變更日誌 (Changelog)，列點說明增加了什麼、刪除了什麼。

修改片段：
{patches_text}

請生成簡潔的變更摘要，使用列點格式，說明主要變更內容。"""
        else:
            # 計算變更統計
            original_lines = original_content.split("\n")
            modified_lines = modified_content.split("\n")
            added_lines = len(modified_lines) - len(original_lines)

            # 提取變更片段（前後各 500 字符）
            diff_text = self._extract_diff_snippet(
                original_content, modified_content, max_length=1000
            )

            prompt = f"""請將以下文檔變更總結為一份 200 字以內的變更日誌 (Changelog)，列點說明增加了什麼、刪除了什麼。

變更統計：
- 原始行數: {len(original_lines)}
- 修改後行數: {len(modified_lines)}
- 行數變化: {added_lines:+d}

變更片段：
{diff_text}

請生成簡潔的變更摘要，使用列點格式，說明主要變更內容。"""

        return prompt

    def _extract_diff_snippet(self, original: str, modified: str, max_length: int = 1000) -> str:
        """
        提取變更片段（簡化版本，比較前後文本）

        Args:
            original: 原始文本
            modified: 修改後文本
            max_length: 最大長度

        Returns:
            變更片段文本
        """
        # 簡單的文本比較（實際可以使用更複雜的 diff 算法）
        if original == modified:
            return "無變更"

        # 找出第一個不同的位置
        min_len = min(len(original), len(modified))
        start_idx = 0
        for i in range(min_len):
            if original[i] != modified[i]:
                start_idx = max(0, i - 100)  # 向前取 100 字符作為上下文
                break

        # 提取變更區域
        snippet_original = original[start_idx : start_idx + max_length]
        snippet_modified = modified[start_idx : start_idx + max_length]

        return f"原始: {snippet_original[:500]}\n\n修改後: {snippet_modified[:500]}"

    def _generate_default_summary(self, original_content: str, modified_content: str) -> str:
        """
        生成默認摘要（當 LLM 生成失敗時使用）

        Args:
            original_content: 原始文件內容
            modified_content: 修改後的文件內容

        Returns:
            默認摘要文本
        """
        original_lines = len(original_content.split("\n"))
        modified_lines = len(modified_content.split("\n"))
        added_lines = modified_lines - original_lines

        if added_lines > 0:
            return f"新增 {added_lines} 行內容"
        elif added_lines < 0:
            return f"刪除 {abs(added_lines)} 行內容"
        else:
            return "文檔內容已修改"
