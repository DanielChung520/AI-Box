# 代碼功能說明: 驗證與 Linter
# 創建日期: 2026-01-11
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-11

"""驗證與 Linter

實現基本驗證和進階驗證功能（結構檢查、長度檢查、樣式檢查、語義漂移檢查、外部參照檢查）。
"""

from typing import Optional

from agents.builtin.document_editing_v2.models import Constraints
from agents.core.editing_v2.error_handler import EditingError, EditingErrorCode
from agents.core.editing_v2.external_reference_checker import ExternalReferenceChecker
from agents.core.editing_v2.markdown_parser import MarkdownParser
from agents.core.editing_v2.semantic_drift_checker import SemanticDriftChecker
from agents.core.editing_v2.style_checker import StyleChecker


class ValidatorLinter:
    """驗證與 Linter

    提供輸出驗證功能。
    """

    def __init__(
        self,
        parser: MarkdownParser,
        original_content: Optional[str] = None,
        context_content: Optional[str] = None,
    ):
        """
        初始化驗證器

        Args:
            parser: Markdown 解析器
            original_content: 原始內容（用於語義漂移檢查）
            context_content: 上下文內容（用於外部參照檢查）
        """
        self.parser = parser
        self.original_content = original_content
        self.context_content = context_content
        self.style_checker: Optional[StyleChecker] = None
        self.semantic_drift_checker: Optional[SemanticDriftChecker] = None
        self.external_reference_checker = ExternalReferenceChecker(context_content=context_content)

    def validate(self, content: str, constraints: Optional[Constraints] = None) -> None:
        """
        驗證內容

        Args:
            content: 內容
            constraints: 約束條件

        Raises:
            EditingError: 驗證失敗時拋出
        """
        # 結構檢查
        self._validate_structure(content)

        # 長度檢查
        if constraints:
            self._validate_length(content, constraints)

        # 進階驗證（如果啟用）
        if constraints:
            # 樣式檢查
            if constraints.style_guide:
                self._validate_style(content, constraints.style_guide)

            # 語義漂移檢查
            if self.original_content:
                self._validate_semantic_drift(content)

            # 外部參照檢查
            if constraints.no_external_reference:
                self._validate_external_reference(content)

    def _validate_structure(self, content: str) -> None:
        """
        驗證結構（標題階層連續性、Markdown 語法）

        Args:
            content: 內容

        Raises:
            EditingError: 結構錯誤時拋出
        """
        # 簡化實現：使用 parser 驗證 Markdown 語法
        try:
            self.parser.parse(content)
        except Exception as e:
            raise EditingError(
                code=EditingErrorCode.VALIDATION_FAILED,
                message=f"Markdown 語法錯誤: {str(e)}",
                details={"error": str(e)},
            )

        # 標題階層連續性檢查（簡化實現）
        # 實際實現需要檢查標題層級是否連續（如 h1 -> h2 -> h3，不能 h1 -> h3）
        lines = content.split("\n")
        previous_level = 0
        for line in lines:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if level > previous_level + 1 and previous_level > 0:
                    raise EditingError(
                        code=EditingErrorCode.VALIDATION_FAILED,
                        message=f"標題階層不連續: 從 h{previous_level} 跳到 h{level}",
                        details={"previous_level": previous_level, "current_level": level},
                    )
                previous_level = level

    def _validate_length(self, content: str, constraints: Constraints) -> None:
        """
        驗證長度（max_tokens、max_chars）

        Args:
            content: 內容
            constraints: 約束條件

        Raises:
            EditingError: 長度違規時拋出
        """
        # max_chars 檢查
        char_count = len(content.encode("utf-8"))
        # 這裡不檢查 max_chars，因為通常由 max_tokens 控制

        # max_tokens 檢查（簡化實現）
        if constraints.max_tokens:
            # 簡化估算：1 token ≈ 4 字符（中文和英文混合）
            estimated_tokens = char_count / 4
            if estimated_tokens > constraints.max_tokens:
                raise EditingError(
                    code=EditingErrorCode.CONSTRAINT_VIOLATION,
                    message=f"內容長度超過限制: 估計 {estimated_tokens:.0f} tokens，限制 {constraints.max_tokens} tokens",
                    details={
                        "estimated_tokens": estimated_tokens,
                        "max_tokens": constraints.max_tokens,
                    },
                )

    def _validate_style(self, content: str, style_guide: str) -> None:
        """
        驗證樣式（語氣、術語、格式）

        Args:
            content: 內容
            style_guide: 樣式指南名稱

        Raises:
            EditingError: 樣式違規時拋出
        """
        if not self.style_checker or self.style_checker.style_guide != style_guide:
            self.style_checker = StyleChecker(style_guide=style_guide)

        violations = self.style_checker.check(content)

        if violations:
            raise EditingError(
                code=EditingErrorCode.VALIDATION_FAILED,
                message=f"樣式檢查失敗: 發現 {len(violations)} 個違規",
                details={
                    "style_guide": style_guide,
                    "violations": violations,
                },
                suggestions=[
                    {
                        "action": "修正樣式違規",
                        "example": violations[0].get("suggestion", ""),
                    }
                ],
            )

    def _validate_semantic_drift(self, content: str) -> None:
        """
        驗證語義漂移（NER 變更率、關鍵詞交集比例）

        Args:
            content: 內容

        Raises:
            EditingError: 語義漂移違規時拋出
        """
        if not self.original_content:
            return

        if not self.semantic_drift_checker:
            self.semantic_drift_checker = SemanticDriftChecker()

        violations = self.semantic_drift_checker.check(self.original_content, content)

        if violations:
            # 合併所有違規信息
            messages = [v.get("message", "") for v in violations]
            raise EditingError(
                code=EditingErrorCode.VALIDATION_FAILED,
                message=f"語義漂移檢查失敗: {'; '.join(messages)}",
                details={
                    "violations": violations,
                },
                suggestions=[
                    {
                        "action": "保持原始內容的語義",
                        "example": violations[0].get("suggestion", ""),
                    }
                ],
            )

    def _validate_external_reference(self, content: str) -> None:
        """
        驗證外部參照（外部 URL、未在上下文中的事實）

        Args:
            content: 內容

        Raises:
            EditingError: 外部參照違規時拋出
        """
        violations = self.external_reference_checker.check(content, no_external_reference=True)

        if violations:
            raise EditingError(
                code=EditingErrorCode.CONSTRAINT_VIOLATION,
                message=f"外部參照檢查失敗: 發現 {len(violations)} 個外部參照",
                details={
                    "violations": violations,
                },
                suggestions=[
                    {
                        "action": "移除外部參照",
                        "example": violations[0].get("suggestion", ""),
                    }
                ],
            )
