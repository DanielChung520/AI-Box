# 代碼功能說明: 提示詞管理服務
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""提示詞管理服務 - 管理LLM提示詞"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# System Prompt定義
WAREHOUSE_AGENT_SYSTEM_PROMPT = """你是一個庫存管理助手（庫管員 Agent），專門負責處理庫存管理相關的業務邏輯。

你的職責：
1. 理解用戶的庫存管理指令
2. 識別用戶要執行的操作類型（查詢料號、查詢庫存、缺料分析、生成採購單等）
3. 提取業務參數（料號、數量等）
4. 理解上下文中的指代（如「剛才查的那個料號」）

支持的操作類型：
- query_part: 查詢物料基本信息
- query_stock: 查詢庫存信息
- analyze_shortage: 缺料分析
- generate_purchase_order: 生成採購單
- adjust_stock: 調整庫存（虛擬）

輸出要求：
- 必須返回有效的 JSON 格式
- 包含識別的意圖（intent）、置信度（confidence）、提取的參數（parameters）
- 如果指令不明確，標記需要澄清（clarification_needed）並提供澄清問題
"""


class PromptManager:
    """提示詞管理服務"""

    def __init__(self) -> None:
        """初始化提示詞管理器"""
        self._logger = logger
        self._system_prompt = WAREHOUSE_AGENT_SYSTEM_PROMPT

    def get_system_prompt(self) -> str:
        """獲取System Prompt

        Returns:
            System Prompt字符串
        """
        return self._system_prompt

    def build_semantic_analysis_prompt(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """構建語義分析提示詞

        Args:
            instruction: 用戶指令
            context: 上下文信息（可選）

        Returns:
            構建好的提示詞
        """
        prompt = f"""分析以下用戶指令，識別意圖並提取參數。

用戶指令：
{instruction}

"""

        # 添加上下文信息（如果提供）
        if context:
            context_str = json.dumps(context, ensure_ascii=False, indent=2)
            prompt += f"""上下文信息：
{context_str}

注意：如果指令中包含指代（如「剛才查的那個料號」），請從上下文中獲取對應的值。

"""

        prompt += """請返回以下 JSON 格式：
{
    "intent": "query_part|query_stock|analyze_shortage|generate_purchase_order|adjust_stock",
    "confidence": 0.0-1.0,
    "parameters": {
        "part_number": "料號（如果可提取）",
        "quantity": 數量（如果可提取）,
        "location": "庫存位置（如果可提取）"
    },
    "clarification_needed": false,
    "clarification_questions": []
}

如果指令不明確，請設置 clarification_needed 為 true，並提供澄清問題。"""

        return prompt

    async def call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> str:
        """調用LLM生成響應

        Args:
            system_prompt: System Prompt
            user_prompt: User Prompt
            temperature: 溫度參數（0-1）
            max_tokens: 最大token數

        Returns:
            LLM響應文本

        Note:
            此方法需要根據實際的LLM服務實現
            可以調用AI-Box的LLM服務或本地LLM
        """
        # TODO: 實現LLM調用邏輯
        # 可以通過AI-Box的LLM服務或本地LLM（如Ollama）調用
        # 這裡先返回一個占位符實現

        self._logger.warning("LLM調用未實現，返回空響應")
        return ""

    def parse_llm_response(self, response: str) -> Dict[str, Any]:
        """解析LLM響應為JSON

        Args:
            response: LLM響應文本

        Returns:
            解析後的JSON字典

        Raises:
            ValueError: 解析失敗時拋出異常
        """
        try:
            # 嘗試直接解析JSON
            return json.loads(response)
        except json.JSONDecodeError:
            # 如果直接解析失敗，嘗試提取JSON部分
            # 移除可能的代碼塊標記
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            try:
                return json.loads(cleaned_response)
            except json.JSONDecodeError as e:
                self._logger.error(f"無法解析LLM響應為JSON: {e}, 響應內容: {response}")
                raise ValueError(f"無法解析LLM響應為JSON: {e}") from e
