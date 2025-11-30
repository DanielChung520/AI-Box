# 代碼功能說明: Prompt Manager 模組適配器（向後兼容）
# 創建日期: 2025-11-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-11-30

"""Prompt Manager 模組適配器 - 重新導出 genai.prompt 的模組"""

# 從 genai 模組重新導出
from genai.prompt.manager import PromptManager  # noqa: F401

__all__ = ["PromptManager"]
