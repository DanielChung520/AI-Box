# 代碼功能說明: MM-Agent 對話鏈 - LangChain 編排
# 創建日期: 2026-01-31
# 創建人: Daniel Chung

"""MM-Agent 對話鏈 - LangChain 編排"""

import os
from typing import Dict, Any, Optional
from pydantic import BaseModel

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

from .translator import Translator, TranslationResult
from .positive_list import PositiveListChecker


class MMChainInput(BaseModel):
    """對話鏈輸入"""

    instruction: str
    context: Optional[Dict[str, Any]] = None


class MMChainOutput(BaseModel):
    """對話鏈輸出"""

    success: bool
    response: str
    translation: Optional[TranslationResult] = None
    needs_clarification: bool = False
    clarification_message: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None


class MMAgentChain:
    """MM-Agent 對話鏈"""

    SYSTEM_PROMPT = """你是一個專業的物料管理助手（MM-Agent）。

你的職責是：
1. 理解用戶關於庫存、採購、銷售的查詢
2. 將自然語言轉換為專業術語
3. 提供準確、專業的回覆

工作流程：
1. 檢查查詢是否在正面表列內
2. 進行語義分析，提取意圖和參數
3. 專業轉譯（tlf19 碼、時間表達式）
4. 執行查詢並生成回覆

回覆要求：
- 使用繁體中文
- 專業但易於理解的語言
- 包含關鍵數據和專業術語說明

當無法理解查詢時，請求用戶澄清。"""

    def __init__(self):
        self._llm = None
        self._translator = Translator()
        self._positive_list = PositiveListChecker()
        self._init_llm()

    def _init_llm(self):
        """初始化 LLM"""
        model = os.getenv("OLLAMA_MODEL", "glm-4.7:cloud")
        base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        self._llm = ChatOllama(
            model=model,
            temperature=0.1,
            base_url=base_url,
        )

    def _check_positive_list(self, instruction: str) -> tuple[bool, str]:
        """L4: 正面表列檢查"""
        return self._positive_list.needs_clarification(instruction)

    def _translate(self, instruction: str) -> TranslationResult:
        """L2: 專業轉譯"""
        return self._translator.translate(instruction)

    def _analyze_intent(self, instruction: str, translation: TranslationResult) -> str:
        """L1: 意圖分析"""
        if translation.tlf19:
            if translation.tlf19 in ["101", "102"]:
                return "purchase"
            elif translation.tlf19 in ["201"]:
                return "material_issue"
            elif translation.tlf19 in ["202"]:
                return "sales"
            elif translation.tlf19 in ["301"]:
                return "scrapping"
        elif "庫存" in instruction:
            return "inventory"
        return "unknown"

    def _generate_response(
        self,
        instruction: str,
        translation: TranslationResult,
        intent: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成回覆"""
        prompt = f"""
用戶查詢：{instruction}

轉譯結果：
- 交易類別：{translation.tlf19} ({translation.tlf19_description})
- 時間表達式：{translation.time_expr}
- 料號：{translation.part_number}
- 數量：{translation.quantity}
- 表格：{translation.table_name}

意圖分類：{intent}

請根據以上信息，用繁體中文生成專業的回覆。
"""

        response = self._llm.invoke([HumanMessage(content=prompt)])
        return response.content if hasattr(response, "content") else str(response)

    def run(self, input_data: MMChainInput) -> MMChainOutput:
        """執行對話鏈"""
        instruction = input_data.instruction
        context = input_data.context or {}

        # L4: 正面表列檢查
        needs_clarification, clar_msg = self._check_positive_list(instruction)
        if needs_clarification:
            return MMChainOutput(
                success=False,
                response="",
                needs_clarification=True,
                clarification_message=clar_msg,
                debug_info={"step": "positive_list_check", "passed": False},
            )

        # L2: 專業轉譯
        translation = self._translate(instruction)

        # L1: 意圖分析
        intent = self._analyze_intent(instruction, translation)

        # 生成回覆
        response = self._generate_response(
            instruction=instruction,
            translation=translation,
            intent=intent,
            context=context,
        )

        return MMChainOutput(
            success=True,
            response=response,
            translation=translation,
            debug_info={
                "step": "completed",
                "intent": intent,
                "translation": translation.model_dump(),
            },
        )

    async def arun(self, input_data: MMChainInput) -> MMChainOutput:
        """異步執行對話鏈"""
        return self.run(input_data)


if __name__ == "__main__":
    chain = MMAgentChain()

    test_cases = [
        MMChainInput(instruction="RM05-008 上月買進多少"),
        MMChainInput(instruction="今天天氣如何"),
        MMChainInput(instruction="RM05-008 庫存還有多少"),
    ]

    for input_data in test_cases:
        print(f"\n{'=' * 60}")
        print(f"輸入: {input_data.instruction}")
        result = chain.run(input_data)

        print(f"成功: {result.success}")
        if result.needs_clarification:
            print(f"需要澄清: {result.clarification_message}")
        else:
            print(f"回覆: {result.response}")
            if result.debug_info:
                print(f"除錯: {result.debug_info}")
